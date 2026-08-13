frappe.ui.form.on("Push Relay Settings", {
  refresh(frm) {
    frm.toggle_display("firebase_section", frm.doc.mode === "Local");
    frm.toggle_display("remote_section", frm.doc.mode === "Remote");

    if (frm.doc.mode === "Local") {
      frm.add_custom_button(__("Test Firebase"), () => {
        frappe.call({
          method: "frappe_push_relay.api.settings.test_firebase",
          freeze: true,
        }).then(() => frappe.show_alert({ message: __("Firebase connection succeeded"), indicator: "green" }));
      });
    }
  },
});
