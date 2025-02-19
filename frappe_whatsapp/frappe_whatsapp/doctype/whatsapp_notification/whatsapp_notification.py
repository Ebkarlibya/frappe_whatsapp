"""Notification."""

import json
import frappe
from frappe.model.document import Document
from frappe.utils.safe_exec import get_safe_globals, safe_exec
from frappe.integrations.utils import make_post_request
from frappe.desk.form.utils import get_pdf_link


class WhatsAppNotification(Document):
    """Notification."""

    def validate(self):
        """Validate."""
        if self.notification_type == "DocType Event":
            fields = frappe.get_doc("DocType", self.reference_doctype).fields
            fields += frappe.get_all(
                "Custom Field",
                filters={"dt": self.reference_doctype},
                fields=["fieldname"]
            )
            if not any(field.fieldname == self.field_name for field in fields):  # noqa
                frappe.throw(f"Field name {self.field_name} does not exists")

    def send_scheduled_message(self) -> dict:
        """Specific to API endpoint Server Scripts."""
        safe_exec(
            self.condition, get_safe_globals(), dict(doc=self)
        )
        language_code = frappe.db.get_value(
            "WhatsApp Templates", self.template,
            fieldname='language_code'
        )
        if language_code:
            for contact in self._contact_list:
                data = {
                    "messaging_product": "whatsapp",
                    "to": self.format_number(contact),
                    "type": "template",
                    "template": {
                        "name": self.template,
                        "language": {
                            "code": language_code
                        },
                        "components": []
                    }
                }

                self.notify(data)
        # return _globals.frappe.flags

    def send_template_message(self, doc: Document):
        """Specific to Document Event triggered Server Scripts."""
        if self.disabled:
            return

        doc_data = doc.as_dict()
        if self.condition:
            # check if condition satisfies
            if not frappe.safe_eval(
                self.condition, get_safe_globals(), dict(doc=doc_data)
            ):
                return

        template = frappe.db.get_value(
            "WhatsApp Templates", self.template,
            fieldname='*'
        )

        if template:
            data = {
                "messaging_product": "whatsapp",
                "to": self.format_number(doc_data[self.field_name]),
                "type": "template",
                "template": {
                    "name": self.template,
                    "language": {
                        "code": template.language_code
                    },
                    "components": []
                }
            }

            # Pass parameter values
            if self.fields:
                parameters = []
                for field in self.fields:
                    parameters.append({
                        "type": "text",
                        "text": doc_data[field.field_name]
                    })

                data['template']["components"] = [{
                    "type": "body",
                    "parameters": parameters
                }]
            if self.url_template == 1:  # كنت حاذفها بالغلط xD
                data['template']["components"].append({
                    "type": "button",
                    "sub_type": "url",
                    "index": "0",
                    "parameters": [
                        {
                            "type": "text",
                            "text": doc.name
                        }
                    ]
                })
            if self.attach_document_print:
                # frappe.db.begin()
                key = doc.get_document_share_key()  # noqa
                frappe.db.commit()
                print_format = "Standard"
                doctype = frappe.get_doc("DocType", doc_data['doctype'])
                if doctype.custom:
                    if doctype.default_print_format:
                        print_format = doctype.default_print_format
                else:
                    default_print_format = frappe.db.get_value(
                        "Property Setter",
                        filters={
                            "doc_type": doc_data['doctype'],
                            "property": "default_print_format"
                        },
                        fieldname="value"
                    )
                    print_format = default_print_format if default_print_format else print_format
                link = get_pdf_link(
                    doc_data['doctype'],
                    doc_data['name'],
                    print_format=print_format
                )

                filename = f'{doc_data["name"]}.pdf'
                url = f'{frappe.utils.get_url()}{link}&key={key}'
                # frappe.log_error(f"Printing document: {doc_data['doctype']} {doc_data['name']} - URL: {url}")
            if template.header_type == 'DOCUMENT':
                data['template']['components'].append({
                    "type": "header",
                    "parameters": [{
                        "type": "document",
                        "document": {
                            "link": url,
                            "filename": filename
                        }
                    }]
                })
            elif template.header_type == 'IMAGE':
                data['template']['components'].append({
                    "type": "header",
                    "parameters": [{
                        "type": "image",
                        "image": {
                            "link": url
                        }
                    }]
                })
            self.content_type = template.header_type.lower()

            self.notify(data, doc_data)

    def notify(self, data, doctype):
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

                    if not self.get("content_type"):
                        self.content_type = 'text'
                    print(response)
                    frappe.get_doc({
                        "doctype": "WhatsApp Message",
                        "type": "Outgoing",
                        "message": str(data['template']),
                        "to": data['to'],
                        "message_type": "Template",
                        "message_id": response['messages'][0]['id'],
                        "content_type": self.content_type
                    }).save(ignore_permissions=True)

                    frappe.msgprint("WhatsApp Message Triggered", indicator="green", alert=True)

        except Exception as e:
            frappe.log_error(f"Error sending WhatsApp message: {e}")
        finally:
            frappe.get_doc({
                "doctype": "WhatsApp Notification Log",
                "template": self.template,
                "meta_data": frappe.flags.integration_request.json()
            }).insert(ignore_permissions=True)

    def on_trash(self):
        """On delete remove from schedule."""
        if self.notification_type == "Scheduler Event":
            frappe.delete_doc("Scheduled Job Type", self.name)

        frappe.cache().delete_value("whatsapp_notification_map")

    def after_insert(self):
        """After insert hook."""
        if self.notification_type == "Scheduler Event":
            method = f"frappe_whatsapp.utils.trigger_whatsapp_notifications_{self.event_frequency.lower().replace(' ', '_')}"  # noqa
            job = frappe.get_doc(
                {
                    "doctype": "Scheduled Job Type",
                    "method": method,
                    "frequency": self.event_frequency
                }
            )

            job.insert()

    def format_number(self, number):
        """Format number."""
        if (number.startswith("+")):
            number = number[1:len(number)]

        return number


def set_property_after_alert(self, doc):
    """This functions gets the field and the name to set in the required doctype

    Args:
        doc (Document): The Document in which to set the property after the alert.
    """
    if self.set_property_after_alert:
        allow_update = True
        if (
                doc.docstatus.is_submitted()
                and not doc.meta.get_field(self.set_property_after_alert).allow_on_submit
        ):
            allow_update = False
        try:
            if allow_update and not doc.flags.in_notification_update:
                fieldname = self.set_property_after_alert
                value = self.property_value

                if doc.meta.get_field(fieldname).fieldtype in frappe.model.numeric_fieldtypes:
                    value = frappe.utils.cint(value)

                print(fieldname, value)
                doc.reload()
                doc.db_set(fieldname, value,  commit=True)

        except Exception:
            self.log_error("Document update failed")
