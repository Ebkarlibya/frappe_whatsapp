// Copyright (c) 2022, Shridhar Patil and contributors
// For license information, please see license.txt
whatsapp_notification = {
  setup_fieldname_select: function (frm) {
    // get the doctype to update fields
    if (!frm.doc.reference_doctype) {
      return;
    }
    frappe.model.with_doctype(frm.doc.reference_doctype, function () {
      let get_select_options = function (df, parent_field) {
        // Append parent_field name along with fieldname for child table fields
        let select_value = parent_field
          ? df.fieldname + "," + parent_field
          : df.fieldname;
        return {
          value: select_value,
          label: df.fieldname + " (" + __(df.label) + ")",
        };
      };
      let get_date_change_options = function () {
        let date_options = $.map(fields, function (d) {
          return d.fieldtype == "Date" || d.fieldtype == "Datetime"
            ? get_select_options(d)
            : null;
        });
        // append creation and modified date to Date Change field
        return date_options.concat([
          { value: "creation", label: `creation (${__("Created On")})` },
          {
            value: "modified",
            label: `modified (${__("Last Modified Date")})`,
          },
        ]);
      };
      let fields = frappe.get_doc("DocType", frm.doc.reference_doctype).fields;
      let options = $.map(fields, function (d) {
        return in_list(frappe.model.no_value_type, d.fieldtype)
          ? null
          : get_select_options(d);
      });
      // set value changed options
      frm.set_df_property(
        "set_property_after_alert",
        "options",
        [""].concat(options)
      );
      // set date changed options
    });
  },
};
frappe.ui.form.on("WhatsApp Notification", {
  refresh: function (frm) {
    whatsapp_notification.setup_fieldname_select(frm);

    frm.trigger("load_template");
    //   reference_doctype: function (frm) {
  },
  reference_doctype: function (frm) {
    whatsapp_notification.setup_fieldname_select(frm);
  },
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
