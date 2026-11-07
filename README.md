# Tasmota Status Decoder integration in Home Assistant

A Home Assistant integration, installable through [HACS](https://hacs.xyz/) or the
built-in Marketplace, that runs the
[decode-status.py](https://github.com/arendst/Tasmota/discussions/17992) script by
Theo Arends and Jacek Ziolkowski against a Tasmota device and shows the decoded
report on a dashboard.

It exposes one service, `tasmota_decoder.run_script`, which takes the device's IP
address and publishes the decoded report on `sensor.tasmota_script_output`:
the short state, plus the whole report in the `full_output` attribute.

## Installation

Add this repository as a custom repository, install it, then add the helpers below
to your `configuration.yaml`.

```yaml
tasmota_decoder:

input_text:
  tasmota_ip_address:
    name: Tasmota IP Address
    pattern: '^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
    mode: text

input_boolean:
  tasmota_decoder_trigger:
    name: Trigger Tasmota Decoder
    initial: off

input_select:
  device_dropdown:
    name: Select a device
    options:
      - "Select a device"
    initial: "Select a device"

template:
  - sensor:
      - name: Selected device IP
        unique_id: tasmota_decoder_selected_device_ip
        state: >
          {% set selected = states('input_select.device_dropdown') %}
          {% if ' - ' in selected %}{{ selected.split(' - ')[1] }}{% endif %}
```

> **Do not remove `input_text.tasmota_ip_address` later on.** It is the address the
> service is called with. If the helper disappears, `states()` returns the literal
> string `unavailable`, and that is what the service receives. See
> [Troubleshooting](#troubleshooting).

Then these automations in `automations.yaml`:

```yaml
- id: 02d20eb0e88240a0b3759823b8f179ff
  alias: Tasmota Call Decoder Service
  triggers:
    - trigger: state
      entity_id: input_boolean.tasmota_decoder_trigger
      from: "off"
      to: "on"
  conditions:
    # A plain "is it non-empty" test is not enough: "unavailable" is non-empty.
    - condition: template
      value_template: >
        {{ states('input_text.tasmota_ip_address')
           | regex_match('^\d{1,3}(\.\d{1,3}){3}$') }}
  actions:
    - action: tasmota_decoder.run_script
      data:
        ip_address: "{{ states('input_text.tasmota_ip_address') }}"
    - action: input_boolean.turn_off
      target:
        entity_id: input_boolean.tasmota_decoder_trigger

- id: 9e0bfc0acb684ec79badac44259c8da8
  alias: Tasmota Request Device Status
  triggers:
    - trigger: time_pattern
      minutes: /1
  actions:
    - action: mqtt.publish
      data:
        topic: cmnd/tasmotas/STATUS
        payload: "5"

- id: "1717242926251"
  alias: Tasmota Set input box to dropdown selected item
  triggers:
    - trigger: state
      entity_id:
        - input_select.device_dropdown
  conditions:
    - condition: template
      value_template: >
        {{ states('sensor.selected_device_ip')
           | regex_match('^\d{1,3}(\.\d{1,3}){3}$') }}
  actions:
    - action: input_text.set_value
      target:
        entity_id: input_text.tasmota_ip_address
      data:
        value: "{{ states('sensor.selected_device_ip') }}"
  mode: single

- id: "1717243239461"
  alias: Tasmota Update Device Dropdown with MQTT Responses
  triggers:
    - trigger: mqtt
      topic: stat/+/STATUS5
  actions:
    - action: input_select.set_options
      data:
        entity_id: input_select.device_dropdown
        options: >
          {% set devices = state_attr('input_select.device_dropdown', 'options') %}
          {% set new_device = trigger.payload_json.StatusNET.Hostname ~ ' - '
             ~ trigger.payload_json.StatusNET.IPAddress %}
          {% if new_device not in devices %}{% set devices = devices + [new_device] %}{% endif %}
          {{ devices }}
  mode: single
```

Finally add a panel view to your dashboard (raw configuration editor, append at the
end of the YAML):

```yaml
- type: panel
  title: Tasmota
  path: tasmota
  cards:
    - type: vertical-stack
      cards:
        - type: horizontal-stack
          cards:
            - type: entities
              entities:
                - input_select.device_dropdown
            - show_name: true
              show_icon: false
              type: button
              tap_action:
                action: perform-action
                perform_action: input_boolean.turn_on
                target:
                  entity_id: input_boolean.tasmota_decoder_trigger
              name: Decode Tasmota
              icon: mdi:lock-remove-outline
        - type: markdown
          content: |-
            {% set full_output = state_attr('sensor.tasmota_script_output', 'full_output') %}
            {% if full_output %} ## Tasmota Script Output {{ full_output }}
            {% else %} No output available. {% endif %}
```

Check the configuration and restart Home Assistant. The automations look for new
Tasmota devices over MQTT every minute and add them to the dropdown.

## Recorder

`sensor.tasmota_script_output` carries the whole report in an attribute, which runs
to roughly 12 KB for a typical device. Every run writes that to the database. The
sensor restores its own last value at startup independently of the recorder, so
excluding it costs you nothing:

```yaml
recorder:
  exclude:
    entities:
      - sensor.tasmota_script_output
```

## Troubleshooting

**`socket.gaierror: [Errno -5] Name has no usable address`**

The service was called with something that is not an IP address, so it was resolved
as a hostname. Almost always `input_text.tasmota_ip_address` no longer exists: a
missing entity makes `states()` return the string `unavailable`, which is then used
as the host.

Check it in Developer Tools → Template:

```jinja
[{{ states('input_text.tasmota_ip_address') }}]
```

If that prints `[unavailable]` or `[unknown]`, look the entity up in Developer Tools
→ States. An `restored: true` attribute means nothing provides it any more — only a
leftover registry row. Delete that row in Settings → Devices & Services → Entities,
then recreate the helper, in that order: otherwise the new one is given
`input_text.tasmota_ip_address_2` and the service keeps reading the dead one.

Since version 1.1.0 the service validates its input, so this case now fails with a
clear message instead of a traceback.

**No output after restarting Home Assistant**

Fixed in 1.1.0. Earlier versions wrote the state directly into the state machine, so
the entity did not exist after a restart until the service ran again.

## Credits

`decode-status.py` is part of [Tasmota](https://github.com/arendst/Tasmota) by Theo
Arends, with the decoding tables by Jacek Ziolkowski, and is distributed here under
the GPL v3 — see [LICENSE](LICENSE). Refresh it from
`arendst/Tasmota/tools/decode-status.py` when new firmware adds options.

The integration itself started as a one hour experiment with ChatGPT, from zero
knowledge of Python and Home Assistant integrations.
