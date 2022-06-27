# hon
Homeassistant component supporting HON cloud.

## pre-requisite
your appliances must be controlled by the hOn mobile application
supported device: Haier Climate tested

## Installation

Create a directory ‘hon’ in custom components sub directory in your HA.
Paste all files in this new directory
Restart HA
Go to Configuration - Devices and add new integration. Search for hOn in search bar and select it
Configure the integration with your hOn username and password
Now you can see one new integration named with your email account with the entities and devices registered with hOn App. You can now add this entities in you panel

## Tested devices

### Climate
- AS35TEDHRA(M1) and AS25TEDHRA(M1) in 2x1 configuration with one outdoor unit
- AS50S2SF2FA-1/1U50S2SJ2FA
