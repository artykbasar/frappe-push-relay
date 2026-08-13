function update_firebase_test_button(frm) {
  frm.remove_custom_button(__("Test Firebase"));

  if (frm.doc.mode === "Local") {
    frm.add_custom_button(__("Test Firebase"), () => {
      frappe.call({
        method: "frappe_push_relay.api.settings.test_firebase",
        freeze: true,
      }).then(() => frappe.show_alert({ message: __("Firebase connection succeeded"), indicator: "green" }));
    });
  }
}

frappe.ui.form.on("Push Relay Settings", {
  refresh(frm) {
    update_firebase_test_button(frm);
  },

  mode(frm) {
    if (frm.doc.mode !== "Local" && frm.doc.allow_other_sites_to_use_this_relay) {
      frm.set_value("allow_other_sites_to_use_this_relay", 0);
    }
    update_firebase_test_button(frm);
  },
});
