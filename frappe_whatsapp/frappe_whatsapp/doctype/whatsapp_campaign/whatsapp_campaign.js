// Copyright (c) 2024, Shridhar Patil and contributors
// For license information, please see license.txt

frappe.ui.form.on('WhatsApp Campaign', {
	refresh: function (frm) {
		if (!frm.doc.__islocal) {
			frm.add_custom_button(__("Send Message"), function () {
				if (frm.doc.customers.length == 0) {
					frappe.msgprint("Please Insert atleast One Customer");
					highlight_field(frm, "customers");
					return;
				}

				if (!frm.doc.template) {
					frappe.msgprint("Please select template");
					highlight_field(frm, "template");
					return;
				}
				const list_of_customers = frm.doc.customers.map((customer) => {
					return customer.phone_number;
				}
				);
				if (list_of_customers.length > 0) {
					const fields = frm.doc.fields.map((customer) => {
						return customer.field_name;
					});
					frappe.call({
						method: "frappe_whatsapp.api.send_whatsapp_messages",
						args: {
							customers: list_of_customers,
							template: frm.doc.template,
							fields: fields,
						},
						callback: function (r) {
							if (r.message) {
								frappe.msgprint("Message Sent Successfully");
							}
						},
					});
				}
			}).addClass("btn-warning").css({ 'color': 'white', 'font-weight': 'bold', "background-color": "orange" });;
		}
	},
	template: function (frm) {
		frm.trigger("load_template");
	},
	load_template: function (frm) {
		frappe.db.get_value(
			"WhatsApp Templates",
			frm.doc.template,
			["template"],
			(r) => {
				if (r && r.template) {
					frm.set_value("code", r.template);
					frm.refresh_field("code");
				}
			}
		);
	},
});

function highlight_field(frm, fieldname) {
	let field = frm.get_field(fieldname);
	if (!field) return;

	let $el = field.$wrapper;

	// set tab as active
	if (field.tab && !field.tab.is_active()) {
		field.tab.set_active();
	}

	if (field.section.is_collapsed()) {
		field.section.collapse(false);
	}

	frappe.utils.scroll_to($el, true, 15);

	let control_element = $el.closest(".frappe-control");
	console.log($el);
	// control_element.addClass("highlight");
	control_element.css("background-color", "#FFB0B6"); // Lighter red color
	setTimeout(() => {
		// control_element.removeClass("highlight");
		control_element.css("background-color", "");
	}, 7000);
	return true;
}