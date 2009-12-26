
class TextRepresentation (object):
	"""
	Kupfer Objects that implement this interface have a plain text
	representation that can be used for Copy & Paste etc
	"""
	def get_text_representation(self):
		"""The default implementation returns the represented object"""
		return self.object

def get_text_representation(obj):
	try:
		return obj.get_text_representation()
	except AttributeError:
		return None
