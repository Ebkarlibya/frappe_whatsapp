# Copyright (c) 2024, Shridhar Patil and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import validate_phone_number_with_country_code

class WhatsAppCampaign(Document):
	def validate(self):
		for phone in self.customers:
			if phone.phone_number:
				validate_phone_number_with_country_code(phone.phone_number,"phone_number")
