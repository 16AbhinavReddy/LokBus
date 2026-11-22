
CREATE TABLE IF NOT EXISTS display_staff_assignments (
    service_date DATE NOT NULL,
    vehicle_number TEXT NOT NULL
        REFERENCES buses(vehicle_number),

    driver_id TEXT NOT NULL
        REFERENCES drivers(driver_id),

    conductor_id TEXT NOT NULL
        REFERENCES conductors(conductor_id),

    driver_is_fallback BOOLEAN NOT NULL DEFAULT FALSE,
    conductor_is_fallback BOOLEAN NOT NULL DEFAULT FALSE,

    PRIMARY KEY (service_date, vehicle_number),

    UNIQUE (service_date, driver_id),
    UNIQUE (service_date, conductor_id)
);

CREATE INDEX IF NOT EXISTS idx_display_staff_vehicle
ON display_staff_assignments(vehicle_number);

