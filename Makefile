# Home Assistant deployment settings
HA_HOST=victor@192.168.1.148
HA_PATH=~/home_assistant/custom_components/easun_inverter

# Command to update Home Assistant custom component
update-ha:
	# Create target directory if it doesn't exist
	ssh $(HA_HOST) "mkdir -p $(HA_PATH)"
	# Copy home_assistant folder contents to custom_components/easun_inverter
	scp -r home_assistant/* $(HA_HOST):$(HA_PATH)/
	# Create easunpy directory and copy the package
	ssh $(HA_HOST) "mkdir -p $(HA_PATH)/easunpy"
	scp -r easunpy/* $(HA_HOST):$(HA_PATH)/easunpy/

.PHONY: update-ha 