
class TextRepresentation (object):
	"""
	Kupfer Objects that implement this interface have a plain text
	representation that can be used for Copy & Paste etc
	"""
	def get_text_representation(self):
		"""The default implementation returns the represented object"""
		return self.object

