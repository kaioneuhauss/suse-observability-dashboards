# Understand the Virtualization dashboards

The Virtualization chart provides four views. Start with the overview, then open the view that matches the problem. The optional Imports module adds a fifth view for VMware imports.

## VM & Host Overview

**Are my VMs or hosts running out of resources?**

Check collection health first, then running VM count, CPU, memory and filesystems. Compare the guest with its host before blaming the VM. Guest available memory, configured RAM, QEMU process memory and host available memory measure different things.

Use cluster, namespace and VM filters to narrow the investigation. Host panels remain at cluster scope: selecting one VM does not turn host usage into that VM's usage.

## VM Performance

**Is the VM using resources, or waiting for them?**

CPU usage together with scheduler waiting helps separate demand from contention. Waiting is an average per vCPU, converted to a percentage. It is not identical to VMware CPU Ready.

Disk latency and I/O waiting can help locate storage bottlenecks. An idle disk has no defined average latency. Guest available memory, major page faults and estimated swap activity help explain memory pressure; available statistics depend on guest support and the balloon driver.

The chart does not enable PSI or change kernel settings.

## Capacity Planning

**How much is assigned, and how much demand have we seen?**

Configured vCPUs and guest RAM count running VM instances. vCPU topology is cores × sockets × threads. The vCPU-to-host-CPU ratio uses logical host CPUs; it is not utilization or a universal overcommit recommendation.

Demand percentiles and peaks use the available history from the last 24 hours. CPU peak is the maximum five-minute average, so very short spikes can be missed. Sample counts help identify incomplete history.

The N-1 memory estimate subtracts the largest host and configured guest RAM from total host RAM. It does not account for overhead, reservations, placement constraints or storage. A positive result does not certify HA. A single-host cluster has no surviving host capacity.

Observe representative workload cycles before changing VM sizes. This project does not resize VMs.

## Storage & Backups

**Which volumes need attention, and what backup records exist?**

Health and attachment charts count active volume states after deduplication. `unknown` on a detached volume is neither confirmed health nor a confirmed failure.

Longhorn latency is converted from nanoseconds to milliseconds. Guest latency can include extra waiting, so the two values need not match. Provisioned size, physical usage, replica reservations and snapshot size are separate measurements and should not be added together.

Last backup, missing backup records and backups older than seven days are review signals. Seven days is the panel's explicit window, not an agreed RPO. Backup codes are shown as New, Pending, In progress, Completed, Error and Unknown. A timestamp or Completed state does not prove application consistency or a successful restore.

The volume filter includes Longhorn volumes that are not VM disks. This is not automatic VM/application backup coverage, and snapshot size is not guaranteed reclaimable space.

## VMware Import Progress

The [Imports module](imports.md) shows controller phases, failures, disk readiness and recorded intervals for VMware imports. It is separate from live migration between Harvester hosts.

## Inspiration and definitions

The contention, capacity and protection topics were inspired by [doccaz/harvester-extra-dashboards](https://github.com/doccaz/harvester-extra-dashboards), revision `e40bb3d751f0b2f0afa765ab7cf0a3afc4767c8d` (Apache-2.0). This project implements native SUSE dashboards; it does not import those Grafana JSON files or require an extra Grafana/Prometheus installation.

See [Metric definitions and limits](metric-contracts.md) for formulas and source versions. This remains a community lab project, not a production recommendation.
