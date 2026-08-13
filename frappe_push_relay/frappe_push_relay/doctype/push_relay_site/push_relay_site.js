frappe.ui.form.on("Push Relay Site", {
  refresh(frm) {
    if (frm.doc.status === "Pending") {
      frm.add_custom_button(__("Approve"), () => {
        frappe.call({
          method: "frappe_push_relay.api.auth.approve_site",
          args: { site: frm.doc.name },
          freeze: true,
        }).then(() => frm.reload_doc());
      });
    }
  },
});
