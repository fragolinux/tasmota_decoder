# Tasmota Status Decoder integration in Home Assistant

Just a 1 hour test with ChatGPT, starting from 0 knowledge on how python and HA integration work, to try to create a Home Assistant Integration compatible with [HACS](https://hacs.xyz/), using the [decode-status.py](https://github.com/arendst/Tasmota/discussions/17992) script by Theo Arends and Jacek Ziolkowski.

Add this repository as custom HACS one, then search for it in HACS and install it, and then add these entities to your `configuration.yaml`

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

    sensor:
      - platform: template
        sensors:
          selected_device_ip:
            value_template: >
              {% set selected = states('input_select.device_dropdown') %}
              {% if selected != 'Select a device' %}
                {{ selected.split(' - ')[1] }}
              {% else %}
                "No IP selected"
              {% endif %}

and these automations to your `automations.yaml`

    - id: 02d20eb0e88240a0b3759823b8f179ff
      alias: Tasmota Call Decoder Service
      description: ''
      trigger:
      - platform: state
        entity_id: input_boolean.tasmota_decoder_trigger
        from: 'off'
        to: 'on'
      condition:
      - condition: template
        value_template: '{{ states(''input_text.tasmota_ip_address'') | length > 0 }}'
      action:
      - service: tasmota_decoder.run_script
        data:
          ip_address: '{{ states(''input_text.tasmota_ip_address'') }}'
      - service: input_boolean.turn_off
        entity_id: input_boolean.tasmota_decoder_trigger

    - id: 9e0bfc0acb684ec79badac44259c8da8
      alias: Tasmota Request Device Status
      description: ''
      trigger:
      - platform: time_pattern
        minutes: /1
      action:
      - service: mqtt.publish
        data:
          topic: cmnd/tasmotas/STATUS
          payload: '5'

    - id: '1717242926251'
      alias: Tasmota Set input box to dropdown selected item
      description: ''
      trigger:
      - platform: state
        entity_id:
        - input_select.device_dropdown
      condition: []
      action:
      - service: input_text.set_value
        target:
          entity_id: input_text.tasmota_ip_address
        data:
          value: '{{ states(''sensor.selected_device_ip'') }}'
      mode: single

    - id: '1717243239461'
      alias: Tasmota Update Device Dropdown with MQTT Responses
      description: ''
      trigger:
      - platform: mqtt
        topic: stat/+/STATUS5
      condition: []
      action:
      - service: input_select.set_options
        data_template:
          entity_id: input_select.device_dropdown
          options: "{% set devices = state_attr('input_select.device_dropdown', 'options')
            %} {% set new_device = trigger.payload_json.StatusNET.Hostname ~ ' - ' ~ trigger.payload_json.StatusNET.IPAddress
            %} {% if new_device not in devices %}\n  {% set devices = devices + [new_device]
            %}\n{% endif %} {{ devices }}\n"
      mode: single

finally add a new panel view to your dashboard (go in raw edit and add this at the end of the yaml):

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
                      action: call-service
                      service: input_boolean.turn_on
                      data: {}
                      target:
                        entity_id: input_boolean.tasmota_decoder_trigger
                    name: Decode Tasmota
                    icon: mdi:lock-remove-outline
              - type: markdown
                content: |-
                  {% set full_output = state_attr('sensor.tasmota_script_output',
                      'full_output') %}

                  {% if full_output %} ## Tasmota Script Output {{ full_output }} {%
                      else %} No output available. {% endif %}


check your configuration, and restart Home Assistant. The automations will search for new tasmota devices via mqtt every minute, adding them to the dropdown box.