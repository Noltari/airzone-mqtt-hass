#!/bin/sh

pip install .

echo ""
echo "### black ###"
black airzone_mqtt_hass
echo "#############"

echo ""
echo "### mypy ###"
mypy --strict airzone_mqtt_hass
echo "############"

echo ""
echo "### ruff ###"
ruff check --fix airzone_mqtt_hass
echo "############"

echo ""
echo "### pylint ###"
pylint airzone_mqtt_hass
echo "##############"
