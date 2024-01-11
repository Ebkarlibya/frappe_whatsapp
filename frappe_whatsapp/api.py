import json
import frappe
from frappe.model.document import Document
from frappe.integrations.utils import make_post_request
@frappe.whitelist()
def send_whatsapp_message(customers,template,fields):
    """Send WhatsApp message to a number"""
    try:
        fields = json.loads(fields)
        customers = json.loads(customers)
        template = frappe.db.get_value(
                "WhatsApp Templates", template,
                fieldname='*'
            )

        if template:
            data = {
                "messaging_product": "whatsapp",
                "to": format_number(customers[0]),
                "type": "template",
                "template": {
                    "name": template.name,
                    "language": {
                        "code": template.language_code
                    },
                    "components": []
                }
            }

            if fields:
                parameters = []
                for field in fields:
                    parameters.append({
                        "type": "text",
                        "text": field
                    })

                data['template']["components"] = [{
                    "type": "body",
                    "parameters": parameters
                }]
    except Exception as e:
        frappe.error_log(frappe.get_traceback(), "WhatsApp Campaign Error")
        frappe.throw("Error while sending WhatsApp Campaign Message")
        print(e)
    try:
        notify(data)
    except Exception as e:
        frappe.throw(f"Failed to send message {str(e)}")
def notify(data):
    """Notify."""
    settings = frappe.get_doc(
        "WhatsApp Settings", "WhatsApp Settings",
    )
    token = settings.get_password("token")

    headers = {
        "authorization": f"Bearer {token}",
        "content-type": "application/json"
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
        frappe.msgprint("WhatsApp Message Sent",
                            indicator="green", alert=True)
    except Exception as e:
        res = frappe.flags.integration_request.json()['error']
        error_message = res.get('Error', res.get("message"))
        frappe.get_doc({
            "doctype": "WhatsApp Notification Log",
            "template": "Text Message",
            "meta_data": frappe.flags.integration_request.json()
        }).insert(ignore_permissions=True)

        frappe.throw(
            msg=error_message,
            title=res.get("error_user_title", "Error")
        )
        
def format_number(number):
    """Format number."""
    if (number.startswith("+")):
        number = number[1:len(number)]

    return number