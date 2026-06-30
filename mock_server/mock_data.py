from __future__ import annotations


USERS = {
    "admin_test": {"password": "123456", "role": "admin", "org_id": "ORG_A"},
    "operator_test": {"password": "123456", "role": "operator", "org_id": "ORG_A"},
    "viewer_test": {"password": "123456", "role": "viewer", "org_id": "ORG_A"},
    "guest_test": {"password": "123456", "role": "guest", "org_id": "ORG_A"},
}

ROLE_PERMISSIONS = {
    "admin": {"device:read", "device:write", "ota:read", "ota:write", "log:read"},
    "operator": {"device:read", "ota:read", "ota:write", "log:read"},
    "viewer": {"device:read", "ota:read", "log:read"},
    "guest": set(),
}

DEVICES = {
    "TEST_DEVICE_001": {
        "device_id": "TEST_DEVICE_001",
        "name": "Smoke Test Sensor 001",
        "status": "online",
        "firmware_version": "1.0.0",
        "org_id": "ORG_A",
    },
    "TEST_DEVICE_002": {
        "device_id": "TEST_DEVICE_002",
        "name": "Smoke Test Sensor 002",
        "status": "online",
        "firmware_version": "1.0.0",
        "org_id": "ORG_A",
    },
    "TEST_DEVICE_OFFLINE": {
        "device_id": "TEST_DEVICE_OFFLINE",
        "name": "Offline Test Sensor",
        "status": "offline",
        "firmware_version": "1.0.0",
        "org_id": "ORG_A",
    },
    "TEST_DEVICE_FOREIGN": {
        "device_id": "TEST_DEVICE_FOREIGN",
        "name": "Foreign Org Sensor",
        "status": "online",
        "firmware_version": "1.0.0",
        "org_id": "ORG_B",
    },
}

FIRMWARES = {
    "FW_0900": {"firmware_id": "FW_0900", "version": "0.9.0", "product": "X-SENSE-SENSOR"},
    "FW_1001": {"firmware_id": "FW_1001", "version": "1.0.0", "product": "X-SENSE-SENSOR"},
    "FW_2001": {"firmware_id": "FW_2001", "version": "2.0.1", "product": "X-SENSE-SENSOR"},
}

