# hOn
[![GitHub](https://img.shields.io/github/license/gvigroux/hon?color=green)](https://github.com/gvigroux/hon/blob/main/LICENSE)

Home Assistant component supporting all devices integreated with hOn cloud.
- 2023/03/23 - I've decided to upgrade the main branch from the 'Full-Rework' branch. The old code is inside the legacy branch.
This move is mandatory to be able maange all devices (even unknown).
I hope that all the peoples that added their devices will test and upgrade this branch. Thanks :)
- 2023/04/12 - Change directory structure to be HACS compliant

## pre-requisite
Your appliances must be controlled by the hOn mobile application
supported device: Haier Climate tested

## Installation

1. Create a directory ‘hon’ containing the code of the custom_components/hon folder in your `custom_components` directory. 
2. OR you can add it through HACS > Integration > ... (top right) > Add custom depot > https://github.com/gvigroux/hon
3. Restart HA
4. Go to `Settings` - `Devices and Services` and `Add integration`. Search for `hOn` in search bar and select it
5. Configure the integration with your hOn username and password
6. Now you can see one new integration named with your email account with the entities and devices registered with hOn App. You can now add this entities in you panel

## Tested devices
This integration has been tested with the following devices.

### Climate
- AS35TEDHRA(M1) and AS25TEDHRA(M1) in 2x1 configuration with one outdoor unit
- AS25XCAHRA and AS35XCAHRA in 3x1 and 1x1 configuration with one/two outdoor units
- AS50S2SF2FA-1/1U50S2SJ2FA
- AS35S2SF1FA-WH and AS25S2SF1FA-WH in 2x1 configuration with one outdoor unit
- Haier AS07TS4HRA-M

### Oven

### Washing Machine
- HW 49AMC/1-80
- HW90-B14959S8U1

### Wine Cooler
- HWS42GDAU1

### Dish Washer
- XIB 6B2D3FB

### WashDryer Machine
- HDQ 496AMBS/1-S

### Tumble Dryer
- haier HD80-A3959

### Air Purifier
- hoover HHP30C011 (Air Purifier 300)
- hoover HHP50CA011 (Air Purifier 500)
