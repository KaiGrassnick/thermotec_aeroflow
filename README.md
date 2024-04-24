# thermotec-aeroflow
Home Assistant Integration for thermotex aeroflow devices

## Disclaimer:
This is completely a private / community project and is __NOT__ related to the Company [`Thermotec AG`](https://thermotec.ag) in any way!<br>
Use this Library / Client on your __own risk__. I am __NOT__ responsible for any __damage, data loss, error or malfunction!__

**THIS IS NOT FINAL NOR ANY STABLE BUILD. THIS PROJECT IS CURRENTLY AT A WORK IN PROGRESS STAGE.**

## Why this Project
This Integration is used for HomeAssistant to provide smart function and is related to my [thermotec aeroflow python library project](https://github.com/KaiGrassnick/py-thermotec-aeroflow-flexismart). 


## How to install

1. Download the latest release
2. Extract and Upload the folder as `thermotec_aeroflow` into your `<config_folder>/custom_components`
   - Make sure the Folder is actually called: `thermotec_aeroflow`. The Name needs to match the Domain.
   - E.g.: If the folder is called: `thermotec_aeroflow-0.0.5` you will not be able to activate the Integration with an Error like this: `{"message":"Invalid handler specified"}`
4. Restart HASSIO
5. Go to integrations
6. Force reload cache ( STRG + F5 or delete Cache )
7. Add new Integration, search for __Thermotec Aeroflow__


## FAQ
- Error: `{"message":"Invalid handler specified"}`
  - Verify the folder you uploaded to `custom_components` is called `thermotec_aeroflow`.
  - It will not work if the folder is called differently. Example: `thermotec_aeroflow-0.0.5` will throw this error

## How to use
Heaters / Zone are detected automatically (if e.g. created via the app)

Example of how a heater might look like

![image](https://user-images.githubusercontent.com/7880861/148777401-1b04b332-cbc9-488c-8114-af22e029025c.png)


## Note
This Project is Licenced under the GPL v3. This decision was made to keep this Project and any improvements Open Source.

Any Trademark, Name or Product is only referenced, but this project does not hold any of these.

- AeroFlow® is the Registered Trademark by [Thermotec AG](https://thermotec.ag)
- [Thermotec AG](https://thermotec.ag) is the Name of the Company behind the Heater and the Gateway
- FlexiSmart is the Product Type / Line of the Gateway / Heater
