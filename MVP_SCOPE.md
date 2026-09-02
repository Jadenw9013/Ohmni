> **Superseded as the product contract.** This is the hackathon-era MVP scope.
> The v1 design envelope, supported archetypes, and unsupported use cases are
> defined in [docs/product/PRODUCT_V1.md](docs/product/PRODUCT_V1.md). This
> document is retained as a historical record.

# MVP Scope

## Supported request profile

The MVP only supports boards that satisfy all of:

- DC input <= 12 V
- low-voltage logic
- 2-layer board preference
- no safety-critical functionality
- no RF-sensitive antenna layout requirements
- no high-current power stages
- standard digital buses
- parts with accessible datasheets

## Supported design blocks

### Power
- USB-C 5 V sink-only input
- basic reverse-polarity protection
- LDO regulation
- simple buck conversion
- decoupling
- basic power indicator LED

### Compute
- ESP32 module
- RP2040
- STM32 selected dev-friendly variants

### Interfaces
- I2C
- SPI
- UART
- GPIO
- ADC for low-frequency sensors

### Human I/O
- push buttons
- LEDs
- simple headers/connectors

## MVP user journey

1. User describes project.
2. System converts request into `RequirementsSpec`.
3. User uploads at least one unfamiliar datasheet.
4. System extracts `ComponentSpec`.
5. System proposes architecture.
6. User sees options and cost tradeoffs.
7. System generates `CircuitIR`.
8. Deterministic checks run.
9. System repairs fixable issues.
10. KiCad artifacts are generated.
11. ERC runs.
12. Supported SPICE checks run.
13. BOM is produced.
14. Final engineering notebook is generated.

## Definition of done

The MVP is done when one complete reference project can pass end-to-end repeatedly without manual code changes.

Recommended reference design:

**ESP32 environmental logger with an I2C environmental sensor, USB-C power, 3.3 V regulation, status LED, programming header, and hand-solder-friendly passive components.**
