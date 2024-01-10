// Copyright (c) 2024, Shridhar Patil and contributors
// For license information, please see license.txt

frappe.ui.form.on('Whatsapp Campaign', {
	// refresh: function(frm) {

	// }
	template: function (frm) {
		frm.trigger("load_template");
	},
	load_template: function (frm) {
		frappe.db.get_value(
			"WhatsApp Templates",
			frm.doc.template,
			["template", "header_type"],
			(r) => {
				if (r && r.template) {
					frm.set_value("header_type", r.header_type);
					frm.refresh_field("header_type");
					if (r.header_type == "DOCUMENT") {
						frm.toggle_display("attach_document_print", true);
					}

					frm.set_value("code", r.template);
					frm.refresh_field("code");
				}
			}
		);
	},
});
