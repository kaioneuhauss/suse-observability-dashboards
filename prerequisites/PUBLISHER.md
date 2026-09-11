# Publisher access: one-time preparation

The content chart needs permission to save dashboards and monitors through the SUSE API. Its Kubernetes ServiceAccount is not a SUSE identity. The Agent's intake token sends telemetry and is not the publisher credential.

## New installation: reuse a default role

The current [SUSE role reference](https://documentation.suse.com/cloudnative/suse-observability/latest/en/setup/security/rbac/rbac_roles.html) lists dashboard and monitor create/read/update/delete permissions for `stackstate-k8s-troubleshooter`. That is sufficient for the operations used by this chart, assuming those permissions are present in the installed version and the publisher owns the managed dashboards.

This default role also grants other operational permissions. Use it when the customer's access policy accepts that scope. For a narrower identity, use the [dedicated roles procedure](../docs/details/OPERATIONS.md#1-cliente-novo-roles-e-secrets-dos-publicadores). Neither option requires an administrator token inside the chart.

The default-role path was checked against current official documentation and rendered Helm configuration. It was not substituted for the lab's existing restricted identities. An administrator should confirm the installed role before creating a customer token; default permissions can vary by release or customization.

### 1. Get one Service Token

If an administrator already supplies an approved token/Secret, skip this step. Otherwise, the administrator opens **CLI** in SUSE and follows that instance's installation and login instructions. Run from an authenticated administrative context, replacing the context and approved expiry date:

```bash
sts service-token create --context YOUR_ADMIN_CONTEXT \
  --name sre-content-publisher \
  --roles stackstate-k8s-troubleshooter \
  --expiration YYYY-MM-DD
```

The token is displayed once. Store it in the customer's vault. Do not paste it into Git, the values file, screenshots or tickets. This is the [official service-token workflow](https://documentation.suse.com/cloudnative/suse-observability/latest/en/use/security/k8s-service-tokens.html). The token button in an OpenTelemetry ingestion setup serves a different purpose.

An administrator can first inspect the installed role with:

```bash
sts rbac describe-permissions --context YOUR_ADMIN_CONTEXT \
  --subject stackstate-k8s-troubleshooter
```

Check `get/create/update/delete-dashboards` and `get/create/update/delete-monitors`. A 403 from a restricted identity does not prove the role is missing; perform this administrative check with an authorized identity.

### 2. Put it in one Kubernetes Secret

In Rancher, open the **central cluster**, choose the content namespace, and create a generic/Opaque Secret:

| Field | Value |
|---|---|
| Name | `suse-observability-publisher-token` |
| Key | `serviceToken` |
| Value | Token from step 1 |

Use the Rancher Secret form's plain value field; Kubernetes handles encoding. Do not create this Secret in every downstream cluster.

Alternatively, if your vault has written only the token (no JSON or trailing newline) to a protected local file, use:

```bash
kubectl create secret generic suse-observability-publisher-token \
  --kubeconfig "$KCFG" --context "$CTX" -n "$CONTENT_NS" \
  --from-file=serviceToken=/secure/path/publisher-token
```

Remove the temporary file after storing the token safely. `kubectl create` deliberately does not overwrite an existing Secret.

### 3. Reference the same Secret twice

`deploy/central/values.yaml` already points `auth.dashboards.existingSecret` and `auth.monitors.existingSecret` to that one Secret. The chart runs two finite Jobs. They use their own CLI executable, so installing or upgrading the chart does not require `sts` on your workstation.

## Existing installations

Keep the dashboard owner token and the existing Secret names. A different token with similar permissions is not automatically the same owner. You may keep separate dashboard and monitor Secrets; edit the two fields in your central values. Do not replace working restricted identities solely to match the simpler new-install example.

Token rotation, expiry and revocation remain administrative tasks. Plan them before expiration and verify both Jobs after a change. To remove all content, run the uninstall procedure while the publisher still has access, then revoke the project-only token.
