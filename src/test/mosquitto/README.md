# Mosquitto

## Ports überprüfen

```bash
docker port mosquitto
```

## User adden

```bash
docker exec mosquitto mosquitto_passwd -b /etc/mosquitto/passwd user password
```