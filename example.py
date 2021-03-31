def on_command(text):
	macro.log("Command entered: " + text)
	macro.log("You had: " + macro.get_buffer())
	macro.set_buffer("[redacted]")
	macro.log("You now have: " + macro.get_buffer())

def on_buffer_changed():
	macro.log(macro.get_buffer())
