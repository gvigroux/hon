# hOn
Home Assistant component supporting hOn cloud.

## pre-requisite
Your appliances must be controlled by the hOn mobile application
supported device: Haier Climate tested

## Installation

1. Create a directory ‘hon’ containing this code in your `custom_components` directory. This can be done by running `git clone https://github.com/gvigroux/hon.git` from within `custom_components`
2. Restart HA
3. Go to `Settings` - `Devices and Services` and `Add integration`. Search for `hOn` in search bar and select it
4. Configure the integration with your hOn username and password
5. Now you can see one new integration named with your email account with the entities and devices registered with hOn App. You can now add this entities in you panel

## Tested devices
This integration has been tested with the following devices.

### Climate
- AS35TEDHRA(M1) and AS25TEDHRA(M1) in 2x1 configuration with one outdoor unit
- AS50S2SF2FA-1/1U50S2SJ2FA

### Oven

### Washing Machine
- HW 49AMC/1-80

### Wine Cooler
- HWS42GDAU1

### WashDryer Machine
- HDQ 496AMBS/1-S
