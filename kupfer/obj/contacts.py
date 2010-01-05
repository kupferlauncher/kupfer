from kupfer.obj.grouping import ContactLeaf, EMAIL_KEY, NAME_KEY

class EmailContact (ContactLeaf):
	def __init__(self, email, name):
		slots = {EMAIL_KEY: email, NAME_KEY: name}
		ContactLeaf.__init__(self, slots, name)

	def repr_key(self):
		return self.object[EMAIL_KEY]

	def get_description(self):
		return self.object[EMAIL_KEY]

