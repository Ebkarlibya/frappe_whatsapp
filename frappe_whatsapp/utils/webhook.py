"""Webhook."""
import frappe
import json
from frappe.integrations.utils import make_post_request
from werkzeug.wrappers import Response


@frappe.whitelist(allow_guest=True)
def webhook():
    """Meta webhook."""
    if frappe.request.method == "GET":
        return get()
    return post()


def get():
    """Get."""
    hub_challenge = frappe.form_dict.get("hub.challenge")
    webhook_verify_token = frappe.db.get_single_value(
        "Whatsapp Settings", "webhook_verify_token"
    )

    if frappe.form_dict.get("hub.verify_token") != webhook_verify_token:
        frappe.throw("Verify token does not match")

    return Response(hub_challenge, status=200)


def post():
    """Post."""
    data = frappe.local.form_dict
    frappe.get_doc({
        "doctype": "WhatsApp Notification Log",
        "template": "Webhook",
        "meta_data": json.dumps(data)
    }).insert(ignore_permissions=True)

    messages = []
    try:
        messages = data["entry"][0]["changes"][0]["value"].get("messages", [])
    except KeyError:
        messages = data["entry"]["changes"][0]["value"].get("messages", [])

    if messages:
        for message in messages:
            if message['type'] == 'text':
                frappe.get_doc({
                    "doctype": "WhatsApp Message",
                    "type": "Incoming",
                    "from": message['from'],
                    "message": message['text']['body']
                }).insert(ignore_permissions=True)
                send_welcome_message(message['from'])
            elif message['type'] == 'request_welcome':
                frappe.get_doc({
                    "doctype": "WhatsApp Message",
                    "type": "Incoming",
                    "from": message['from'],
                    "message": 'Request Welcome'
                }).insert(ignore_permissions=True)
                send_welcome_message(message['from'])
    else:
        changes = None
        try:
            changes = data["entry"][0]["changes"][0]
        except KeyError:
            changes = data["entry"]["changes"][0]
        update_status(changes)
    return

def send_welcome_message(phone_number):
    """Send welcome message."""
    settings = frappe.get_doc(
        "WhatsApp Settings", "WhatsApp Settings",
    )
    token = settings.get_password("token")
    template = frappe.get_doc(
        "WhatsApp Templates", "welcome_message",
    )
    headers = {
        "authorization": f"Bearer {token}",
        "content-type": "application/json"
    }
    data = {
                    "messaging_product": "whatsapp",
                    "to": phone_number,
                    "type": "template",
                    "template": {
                        "name": template.name,
                        "language": {
                            "code": template.language_code
                        },
                        "components": []
                    }
                }
    try:
        response = make_post_request(
            f"{settings.url}/{settings.version}/{settings.phone_id}/messages",
            headers=headers, data=json.dumps(data)
        )
        frappe.get_doc({
                "doctype": "WhatsApp Message",
                "type": "Outgoing",
                "message": str(data['template']),
                "to": data['to'],
                "message_type": "Template",
                "message_id": response['messages'][0]['id']
            }).save(ignore_permissions=True)

    except Exception as e:
        res = frappe.flags.integration_request.json()['error']
        error_message = res.get('Error', res.get("message"))
        frappe.throw(
            msg=error_message,
            title=res.get("error_user_title", "Error")
        )
def update_status(data):
    """Update status hook."""
    if data.get("field") == "message_template_status_update":
        update_template_status(data['value'])

    elif data.get("field") == "messages":
        update_message_status(data['value'])


def update_template_status(data):
    """Update template status."""
    frappe.db.sql(
        """UPDATE `tabWhatsApp Templates`
        SET status = %(event)s
        WHERE id = %(message_template_id)s""",
        data
    )


def update_message_status(data):
    """Update message status."""
    id = data['statuses'][0]['id']
    status = data['statuses'][0]['status']
    conversation = data['statuses'][0].get('conversation', {}).get('id')
    name = frappe.db.get_value("WhatsApp Message", filters={"message_id": id})

    doc = frappe.get_doc("WhatsApp Message", name)
    doc.status = status
    if conversation:
        doc.conversation_id = conversation
    doc.save(ignore_permissions=True)
