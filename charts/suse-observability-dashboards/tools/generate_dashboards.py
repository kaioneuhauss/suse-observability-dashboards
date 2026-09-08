#!/usr/bin/env python3
"""Generate the portable SUSE Observability dashboard definitions."""
from pathlib import Path
import json
import re
import yaml

HERE = Path(__file__).resolve().parent.parent
OUT = HERE / "dashboards"
GREEN, BLUE, AMBER, RED, PURPLE = "#2E8540", "#1976B9", "#E69F00", "#D32F2F", "#7651A8"

def query(alias, expression):
    return {"kind": "TimeSeriesQuery", "spec": {"plugin": {"kind": "PrometheusTimeSeriesQuery", "spec": {"alias": alias, "query": expression}}}}

def stable_display_query(alias, expression):
    # SUSE 2.10.2 can sort aliases independently from values when expanding a
    # legend. Project the complete display identity into the only result label,
    # so the backend and UI have the same ordering. This changes display queries
    # only, never collected metrics or monitor labels. Aliases must be unique.
    parts = re.split(r'\$\{([^}]+)\}', alias)
    if len(parts) > 1:
        labels = parts[1::2]
        separators = parts[2:-1:2]
        if len(set(separators)) <= 1:
            sep = separators[0] if separators else ""
            args = ", ".join(json.dumps(label) for label in labels)
            expression = f'label_join(({expression}), "sre_series", {json.dumps(sep, ensure_ascii=False)}, {args})'
        else:
            expression = f'label_join(({expression}), "sre_series", "", {json.dumps(labels[0])})'
            for sep, label in zip(separators, labels[1:]):
                expression = f'label_join(({expression}), "sre_series", {json.dumps(sep, ensure_ascii=False)}, "sre_series", {json.dumps(label)})'
        if parts[0] or parts[-1]:
            replacement = json.dumps(parts[0] + '$1' + parts[-1], ensure_ascii=False)
            expression = f'label_replace(({expression}), "sre_series", {replacement}, "sre_series", "(.*)")'
        expression = f'max by (sre_series) ({expression})'
        alias = "${sre_series}"
    return {"kind": "TimeSeriesQuery", "spec": {"plugin": {"kind": "PrometheusTimeSeriesQuery", "spec": {"alias": alias, "query": expression}}}}

def number_format(unit, decimals):
    # "decimal" is NOT a supported SUSE unit: it silently falls back to Short.
    # Verified in the 2.10.2 widget editor: None renders 5451, not 5 K.
    return {"decimalPlaces": decimals, "unit": "none" if unit in ("decimal", "cores") else unit}

def end_value(expression):
    # VictoriaMetrics derives implicit instant-selector lookback from the query
    # step. A 1s evaluation wrapper must not turn 30-60s inventory samples into
    # missing data (or a false zero through an inventory fallback). Keep the
    # usual explicit 5m freshness window for instant metric selectors. Existing
    # rate/increase/histogram windows retain their own meaning.
    selector = re.compile(r'([a-zA-Z_:][a-zA-Z0-9_:]*\{(?:[^"{}]|"(?:\\.|[^"\\])*")*\})(\s*\[[^\]]+\])?(\s*@\s*(?:end\(\)|start\(\)|[0-9.]+))?')
    def fresh(match):
        metric, window, at = match.groups()
        return match.group(0) if window else f'last_over_time({metric}[5m]{at or ""})'
    return f'last_over_time(({selector.sub(fresh, expression)})[1s:1s] @ end())'

def stat(name, description, expression, unit="short", decimals=0, color=BLUE, alias="Value", steps=None):
    # The UI reduces a range to its last available value, which can retain an
    # old rate/latency after traffic or telemetry disappears. Evaluate the card
    # only at the selected end, including its inventory joins. The one-second
    # subquery is an evaluation wrapper, not the metric's scrape interval.
    expression = end_value(expression)
    return {"spec": {"display": {"name": name, "description": description}, "plugin": {"kind": "StatChart", "spec": {
        "calculation": "last", "format": number_format(unit, decimals), "sparkline": False, "valueFontSize": 40,
        "thresholds": {"defaultColor": color, "steps": steps or []}}}, "queries": [query(alias, expression)]}}

def multistat(name, description, expression, unit="short", decimals=0, color=BLUE, alias="${pod_name}", steps=None):
    return {"spec": {"display": {"name": name, "description": description}, "plugin": {"kind": "StatChart", "spec": {
        "calculation": "last", "format": number_format(unit, decimals), "sparkline": False, "valueFontSize": 28,
        "thresholds": {"defaultColor": color, "steps": steps or []}}}, "queries": [query(alias, expression)]}}

def utilization_gauge(name, description, expression, alias):
    # Schema observed in SUSE 2.10.2's native GaugeChart YAML editor.
    return {"spec":{"display":{"name":name,"description":description},"plugin":{"kind":"GaugeChart","spec":{
        "calculation":"last","format":{"unit":"percentunit","decimalPlaces":1},"max":1,
        "thresholds":{"mode":"absolute","defaultColor":GREEN,"steps":[{"color":AMBER,"value":0.8},{"color":RED,"value":0.9}]}}},
        "queries":[query(alias,end_value(f'topk(1, ({expression}))'))]}}

def ranked_multistat(name, description, expression, unit="short", decimals=0, color=BLUE, alias="${pod_name}", steps=None, count=5):
    panel=multistat(name,description,expression,unit,decimals,color,alias,steps)
    panel["spec"]["queries"]=[]
    for rank in range(1,count+1):
        ranked=f'topk({rank}, ({expression}))'
        if rank > 1:
            ranked=f'({ranked}) unless (topk({rank-1}, ({expression})))'
        panel["spec"]["queries"].append(query(f"{rank}. {alias}",ranked))
    return panel

def timeseries(name, description, queries, unit="short", decimals=2, steps=None, legend="right"):
    return {"spec": {"display": {"name": name, "description": description}, "plugin": {"kind": "TimeSeriesChart", "spec": {
        "legend": {"mode": "list", "position": legend, "show": True, "values": []},
        "thresholds": {"mode": "absolute", "steps": []}, "visual": {"connectNulls": False},
        "yAxis": {"format": number_format(unit, decimals), "show": True}}}, "queries": queries}}

def series_table(name, description, expression, alias, unit="none", decimals=0, values=True):
    """Native TimeSeriesChart table legend: one series per row, full labels.

    SUSE 2.10.2 has no standalone TableChart plugin. Do not invent one.
    For inventory lists hide the value column and numeric axis, preserving names.
    """
    panel = timeseries(name, description, [query(alias, expression)], unit, decimals, legend="bottom")
    spec = panel["spec"]["plugin"]["spec"]
    spec["legend"].update(mode="table", values=["last"] if values else [])
    spec["yAxis"]["show"] = values
    return panel

def named_empty(expression, text, alias_label="item"):
    # Empty inventory is a labelled absence, never an unlabeled healthy metric.
    text="No matching items; check filters and collection coverage"
    return f'({expression}) or on() label_replace(vector(0), "{alias_label}", "{text}", "", "")'

def barchart(name, description, queries, unit="short", decimals=2, steps=None):
    panel = timeseries(name, description, queries, unit, decimals, steps, "right")
    panel["spec"]["plugin"]["kind"] = "BarChart"
    return panel

def markdown(name, text):
    return {"spec": {"display": {"name": name, "description": "Scope and interpretation."}, "plugin": {"kind": "Markdown", "spec": {"text": text}}, "queries": []}}

def variable(name, display, label, matcher, description):
    return {"perseslistvariable": {"kind": "ListVariable", "spec": {
        "name": name, "display": {"name": display, "description": description}, "allowAllValue": True,
        "allowMultiple": True, "customAllValue": ".*", "sort": "alphabetical-asc",
        # Exact representation produced by the SUSE 2.10.2 editor for Everything.
        # A bare Perses string/array is not the SUSE default-value union.
        "defaultValue": {"perseslistvariabledefaultsinglevalue": {"kind": "singleValue", "singleValue": '{"type":"Everything"}'}, "perseslistvariabledefaultslicevalues": None},
        "plugin": {"kind": "MetricLabelValues", "spec": {"labelName": label, "matchers": [matcher]}}}},
        "persestextvariable": None}

def row(height, *keys):
    return {"height": height, "keys": keys}

def layout(rows, intro=False):
    items=[]; y=0
    if intro:
        items.append({"x":0,"y":0,"width":24,"height":int(intro),"content":{"$ref":"#/spec/panels/guide"}}); y=int(intro)
    for group in rows:
        explicit_height = group.get("height") if isinstance(group, dict) else None
        group = group["keys"] if isinstance(group, dict) else group
        width=24//len(group)
        height=explicit_height or (4 if len(group)<=2 or any(key.endswith("Top") for key in group) else 2)
        for index,key in enumerate(group):
            items.append({"x":index*width,"y":y,"width":width,"height":height,"content":{"$ref":f"#/spec/panels/{key}"}})
        y+=height
    return [{"kind":"Grid","spec":{"items":items}}]

def dashboard(name, description, panels, rows, variables, intro=False):
    presentation=yaml.safe_load((HERE/'tools/presentation-en.yaml').read_text())[name]
    removed=set(presentation.get('remove',[]))
    for key in removed:panels.pop(key)
    rows=[row(r['height'],*[k for k in r['keys'] if k not in removed]) for r in rows]
    rows=[r for r in rows if r['keys']]
    for key,panel in panels.items():
        title,desc=presentation['panels'][key]
        panel['spec']['display']={'name':title,'description':desc}
    panels['guide']['spec']['plugin']['spec']['text']=presentation['guide']
    aliases={'Services':'Applications','Request bytes/s':'Incoming bytes/s','Response bytes/s':'Outgoing bytes/s','Mean latency':'Average response time','Mean':'Average','p50':'Half of calls (p50)','p95':'95 of 100 calls (p95)','p99':'99 of 100 calls (p99)'}
    for panel in panels.values():
        for q in panel['spec'].get('queries',[]):
            spec=q['spec']['plugin']['spec'];spec['alias']=aliases.get(spec['alias'],spec['alias'])
    description=presentation['description']
    for v,label in zip(variables,presentation['filters']):
        v['perseslistvariable']['spec']['display']={'name':label,'description':'Select one or more values. After changing a parent filter, reset the following filters to Everything.'}
    # Milliseconds are explicit in titles and values; no unknown unit fallback.
    for key in presentation.get('milliseconds',[]):
        p=panels[key]['spec'];plugin=p['plugin']['spec']
        fmt=plugin.get('format',plugin.get('yAxis',{}).get('format'))
        fmt.update(unit='none',decimalPlaces=2)
        for q in p['queries']:
            qs=q['spec']['plugin']['spec'];qs['query']='('+qs['query']+') * 1000'
        for step in plugin.get('thresholds',{}).get('steps',[]):step['value']*=1000
    for panel in panels.values():
        panel["spec"]["queries"] = [stable_display_query(q["spec"]["plugin"]["spec"]["alias"], q["spec"]["plugin"]["spec"]["query"]) for q in panel["spec"].get("queries", [])]
    return {"name":name,"description":description,"scope":"publicDashboard","dashboard":{
        "metadata":{"project":'{"saveVariables":false}'},"spec":{"layouts":layout(rows,2 if intro and name in ("Traefik Ingress Health","Workload Resource Efficiency") else intro),"panels":panels,"variables":variables}}}

def application_dashboard():
    # Health/readiness/metrics endpoints are operational traffic. Excluding them keeps the
    # request KPIs aligned with user/business traffic while preserving generic auto-discovery.
    selector='cluster_name=~"${app_cluster}",service_name=~"${instrumented_service}",http_route!~"(?i).*(health|ready|live|metrics).*"'
    total=f'http_server_requests_total{{{selector}}}'
    rate=f'rate({total}[5m])'
    success_1h=f'increase(http_server_requests_total{{{selector},status_class=~"2xx|3xx"}}[1h])'
    errors_1h=f'increase(http_server_requests_total{{{selector},status_class="5xx"}}[1h])'
    buckets=f'rate(http_server_request_duration_seconds_bucket{{{selector}}}[5m])'
    buckets_1h=f'increase(http_server_request_duration_seconds_bucket{{{selector}}}[1h])'
    panels={
      "guide": markdown("How request counting works", "**Business request scope:** only services that publish `http_server_requests_*` metrics are listed. Common health, readiness, liveness and `/metrics` routes are excluded. **Rolling windows:** `last 1h`, `24h` and `30d` count traffic still inside that moving window; they are not counters since the dashboard was opened. A 200-request benchmark increments the raw application counter by exactly 200, while a rolling total can change at the same time as older requests leave the window. New instrumentation and retention can leave 24h or 30d windows incomplete; they are not a calendar-day or month total. Prometheus `increase()` is scrape-based and the displayed total is rounded to the nearest request. Counts use the native None unit and show every digit. **Automatic onboarding:** a new service appears when its metrics contain `cluster_name`, `service_name`, `http_route` and `status_class`; latency also requires the `http_server_request_duration_seconds_bucket` histogram."),
      "rps": stat("Average throughput · rolling 1h", "Business-request increase over the last rolling hour divided by 3,600 seconds. Health and metrics routes are excluded.", f"(sum(increase({total}[1h])) / 3600)", "reqps", 2, BLUE, "Requests/s"),
      "requests1h": stat("Business requests · rolling 1h", "Rounded count of completed business requests still inside the last rolling hour.", f"round(sum(increase({total}[1h])), 1)", "decimal", 0, BLUE, "Requests"),
      "requests24h": stat("Business requests · rolling 24h", "Rounded count of completed business requests still inside the last rolling 24 hours.", f"round(sum(increase({total}[24h])), 1)", "decimal", 0, GREEN, "Requests"),
      "requests30d": stat("Business requests · rolling 30d", "Rounded 30-day business-request count, bounded by available metric retention.", f"round(sum(increase({total}[30d])), 1)", "decimal", 0, PURPLE, "Requests"),
      "counter": stat("Raw counter · since app restart", "Exact sum of the selected application counters since their processes last restarted. Use this panel to verify a controlled benchmark; unlike rolling windows it resets when an application instance restarts.", f"sum({total})", "decimal", 0, PURPLE, "Requests"),
      "success": stat("Successful responses · last 1h", "Share of 2xx and 3xx responses. Unavailable without traffic.", f"((sum({success_1h}) or (sum(increase({total}[1h])) * 0)) / (sum(increase({total}[1h])) > 0))", "percentunit", 2, RED, "Success", [{"color":AMBER,"value":0.95},{"color":GREEN,"value":0.99}]),
      "error5xx": stat("Server errors · last 1h", "Share of 5xx responses. Unavailable without traffic.", f"((sum({errors_1h}) or (sum(increase({total}[1h])) * 0)) / (sum(increase({total}[1h])) > 0))", "percentunit", 2, GREEN, "5xx", [{"color":AMBER,"value":0.01},{"color":RED,"value":0.05}]),
      "p95_1h": stat("p95 latency · 1h · seconds", "95% of completed requests in the last hour were at or below this server-side duration. No requests means the percentile is unavailable, not zero latency.", f"histogram_quantile(0.95, sum by (le) ({buckets_1h}))", "seconds", 3, GREEN, "p95", [{"color":AMBER,"value":0.5},{"color":RED,"value":1.0}]),
      "throughput": timeseries("Traffic by route", "Request throughput grouped by service and normalized server route.", [query("${cluster_name} · ${service_name} · ${http_route}",f"sum by (cluster_name,service_name,http_route) ({rate})")], "reqps", 2),
      "outcomes": timeseries("Response outcomes", "Request rate by HTTP status class.", [query("${status_class}",f"sum by (status_class) ({rate})")], "reqps", 2),
      "errorRoutes": timeseries("HTTP errors by route and code", "Rates over five minutes, grouped by normalized route and exact HTTP response code. A point is a measurement window, not an individual request timestamp.", [query("${cluster_name} · ${service_name} · ${http_route} · HTTP ${http_response_status_code}",f'sum by (cluster_name,service_name,http_route,http_response_status_code) (rate(http_server_requests_total{{{selector},status_class=~"4xx|5xx"}}[5m]))')], "reqps", 3),
      "errorTotals": series_table("HTTP errors by route · last hour", "Estimated counts by application, route, method and HTTP code. Use application/access logs for exact requests and timestamps; a status code alone does not establish the root cause.",f'round(sum by (cluster_name,service_name,http_route,http_request_method,http_response_status_code) (increase(http_server_requests_total{{{selector},status_class=~"4xx|5xx"}}[1h] @ end())), 1)',"${cluster_name} · ${service_name} · ${http_request_method} ${http_route} · HTTP ${http_response_status_code}","none",0),
      "latency": timeseries("Request latency percentiles", "Server-side p50, p95 and p99 latency from the request histogram.", [
          query("p50",f"histogram_quantile(0.50, sum by (le) ({buckets}))"),query("p95",f"histogram_quantile(0.95, sum by (le) ({buckets}))"),query("p99",f"histogram_quantile(0.99, sum by (le) ({buckets}))")], "seconds", 3, [{"color":AMBER,"value":0.5},{"color":RED,"value":1.0}]),
      "routeTotals": series_table("Business requests by route · rolling 1h", "One row per cluster, service and normalized route, with the full rounded request count.", f"round(sum by (cluster_name,service_name,http_route) (increase({total}[1h] @ end())), 1)", "${cluster_name} · ${service_name} · ${http_route}", "none", 0),
      "slowServices": series_table("Slowest services · p95 seconds over 1h", "Top 10 service p95 values from the server histogram. Empty / NaN means no sampled requests, not zero latency.", f"topk(10, histogram_quantile(0.95, sum by (cluster_name,service_name,le) ({buckets_1h})))", "${cluster_name} · ${service_name}", "seconds", 3),
      "routeVolume": timeseries("Request volume by route", "Requests completed during each dashboard sampling interval, grouped by route.", [query("${http_route}",f"sum by (http_route) (increase({total}[${{__rate_interval}}]))")], "none", 0),
    }
    variables=[variable("app_cluster","Cluster","cluster_name",'{__name__=~"http_server_requests_total|http_server_active_requests"}',"Cluster with application-level instrumentation."),variable("instrumented_service","Instrumented service","service_name",'{__name__=~"http_server_requests_total|http_server_active_requests",cluster_name=~"${app_cluster}"}',"Only services publishing application-side HTTP metrics.")]
    rows=[row(2,"rps","requests1h","counter"),row(2,"requests24h","requests30d","p95_1h"),row(2,"success","error5xx"),row(2,"routeTotals"),row(3,"slowServices"),row(3,"throughput","outcomes"),row(3,"errorRoutes","latency"),row(3,"errorTotals"),row(3,"routeVolume")]
    return dashboard("Dashboard - Instrumented apps","Application-only golden signals with full request counts, rolling-window semantics, errors and server latency.",panels,rows,variables,True)

def resource_dashboard():
    f='cluster_name=~"${workload_cluster}",namespace=~"${workload_namespace}"'
    keys="cluster_name,namespace,pod_name,container"
    pods="cluster_name,namespace,pod_name"
    active=f'max by ({keys}) (last_over_time(kubernetes_state_container_running{{{f}}}[5m] @ end()) == 1)'
    # Runtime metrics can have extra process/image labels; deduplicate BEFORE summing.
    cpu=f'max by ({keys}) (avg_over_time(container_cpu_usage{{{f}}}[5m] @ end())) / 1000000'
    mem=f'max by ({keys}) (avg_over_time(container_memory_working_set{{{f}}}[5m] @ end()))'
    def config(resource, suffix):
        return f'max by ({keys}) (last_over_time(kubernetes_state_container_{resource}_{suffix}{{{f}}}[5m] @ end()))'
    cpu_req=config("cpu","requested")+' * 1000'
    cpu_lim=config("cpu","limit")+' * 1000'
    mem_req=config("memory","requested")
    mem_lim=config("memory","limit")
    alias="${cluster_name} · ${namespace} · ${pod_name} · ${container}"
    panels={"guide":markdown("Resource definitions", "**CPU is mCPU:** 1000 mCPU = 1 core/vCPU. **Memory is GiB/MiB, with two decimals.** Use is the container working set averaged over 5 minutes; RSS and JVM heap are different measurements. Requests reserve scheduling capacity; limits constrain containers. A pod can have one container configured and another missing: the lists inspect every running container. CPU above request is allowed; absent CPU limits may be intentional. These are container metrics. See **Harvester VM & Host Health** for guest OS memory. Lists show full cluster, namespace and pod names; the numeric flags are hidden. No configured limit is not a zero-byte ceiling.")}
    missing_sets=[]
    for kind,title,actual,requested,limited,unit,decimals in [
        ("cpu","CPU",cpu,cpu_req,cpu_lim,"none",1),
        ("mem","Memory",mem,mem_req,mem_lim,"bytes(IEC)",2)]:
        top=f'topk(5, sum by ({pods}) ({actual}))'
        pa="${cluster_name} · ${namespace} · ${pod_name}"
        panels[kind+"UsageTop"]=series_table(title+(" use (mCPU)" if kind=="cpu" else " working set")+" · top 5 pods", "Current five-minute average. Same pod identities are used in the adjacent request and limit tables.",top,pa,unit,decimals)
        for suffix,word,expr in [("RequestTop","request",requested),("LimitTop","limit",limited)]:
            scoped=f'sum by ({pods}) ({expr}) and on ({pods}) ({top})'
            panels[kind+suffix]=series_table(title+" "+word+(" (mCPU)" if kind=="cpu" else "")+" · same pods", "Sum of configured regular-container values; absent configuration remains absent, not zero. Check the missing-container list for partially configured pods.",scoped,pa,unit,decimals)
        for suffix,word,expr in [("RequestMissingList","request",requested),("LimitMissingList","limit",limited)]:
            missing=f'({active}) unless on ({keys}) ({expr} > 0)'
            affected=f'max by ({pods}) ({missing})'
            # Count a pod once per category, even when several containers lack
            # the setting. Return zero only with a running-container inventory.
            count=f'count({affected}) or ((count({active}) > 0) * 0)'
            panels[kind+suffix]=stat("Pods missing "+title+" "+word, "Count of distinct pods with at least one running regular container without this positive setting. Missing inventory is not a healthy zero.",count,"none",0,BLUE,"Pods")
            missing_sets.append(f'label_replace(({affected}), "missing_setting", "{title} {word}", "pod_name", ".*")')
        incomplete=f'max by ({pods}) (({active}) unless on ({keys}) ({limited} > 0)) or max by ({pods}) (({active}) unless on ({keys}) ({actual}))'
        pod_ratio=f'((sum by ({pods}) (({actual}) and on ({keys}) ({active}))) / (sum by ({pods}) (({limited}) and on ({keys}) ({active})))) unless on ({pods}) ({incomplete})'
        panels[kind+'UseGauge']=utilization_gauge(title+' use versus pod limit', 'The highest measured pod ratio at the selected end. Includes only pods where every running regular container has a positive limit and usage data. Colors are initial references: orange at 80%, red at 90%. Individual container risks are shown below.',pod_ratio,"${cluster_name} · ${namespace} · ${pod_name}")
    missing_pods=' or '.join('('+expr+')' for expr in missing_sets)
    panels['missingSettingsPods']=series_table("Pods with incomplete resource settings", "One row per pod and missing setting, with cluster and namespace. A pod can occur in several categories. Check its regular containers to find the setting to change.",missing_pods,"${cluster_name} · ${namespace} · ${pod_name} · ${missing_setting}",values=False)
    panels["memoryRisk"]=series_table("Memory / limit · worst 10 containers", "One-hour peak working set / positive memory limit. Container-level comparison catches a single container near OOM that pod totals could hide.",f'topk(10, (max by ({keys}) (max_over_time(container_memory_working_set{{{f}}}[1h] @ end())) / ({mem_lim})) and on ({keys}) ({mem_lim} > 0))',alias,"percentunit",2)
    panels["cpuReservation"]=series_table("CPU / request · worst 10 containers", "Five-minute use divided by a positive request. Values above 100% are permitted and indicate reservation sizing, not CPU-limit violation.",f'topk(10, (({cpu}) / ({cpu_req})) and on ({keys}) ({cpu_req} > 0))',alias,"percentunit",1)
    panels["throttling"]=series_table("CPU throttling · worst 10 containers", "Agent CPU period signals are rates. Ratio of throttled to elapsed periods over five minutes; no extra rate() is applied to these Agent metrics.",f'topk(10, max by ({keys}) (avg_over_time(container_cpu_throttled_periods{{{f}}}[5m])) / clamp_min(max by ({keys}) (avg_over_time(container_cpu_elapsed_periods{{{f}}}[5m])), 0.001))',alias,"percentunit",2)
    panels["restarts"]=series_table("Container restarts · rolling 1h", "All containers with observed restarts in the rolling hour. Empty means no positive increase in the collected series; check telemetry coverage. Correlate previous logs, Last State and probes.",f'max by ({keys}) (increase(kubernetes_state_container_restarts{{{f}}}[1h])) > 0',alias,"none",0)
    panels["workingSetRSS"]=timeseries("Working set and RSS · top 5 pods", "Working set includes non-inactive cache and kernel memory; RSS measures resident anonymous memory. Neither is identical to JVM heap.",[
        query("Working set · ${cluster_name} · ${namespace} · ${pod_name}",f'topk(5, sum by ({pods}) (container_memory_working_set{{{f}}}))'),
        query("RSS · ${cluster_name} · ${namespace} · ${pod_name}",f'sum by ({pods}) (container_memory_rss{{{f}}}) and on ({pods}) topk(5, sum by ({pods}) (container_memory_working_set{{{f}}}))')],"bytes(IEC)",2)
    variables=[variable("workload_cluster","Cluster","cluster_name","container_cpu_usage","Cluster whose container metrics will be compared."), variable("workload_namespace","Namespace","namespace",'kubernetes_state_container_running{cluster_name=~"${workload_cluster}"}',"Namespace scoped to the selected clusters.")]
    rows=[row(2,"cpuUseGauge","memUseGauge"),row(2,"cpuRequestMissingList","cpuLimitMissingList","memRequestMissingList","memLimitMissingList"),row(3,"missingSettingsPods"),row(3,"cpuUsageTop","cpuRequestTop","cpuLimitTop"),row(3,"memUsageTop","memRequestTop","memLimitTop"),row(3,"memoryRisk","cpuReservation"),row(3,"throttling","restarts"),row(3,"workingSetRSS")]
    return dashboard("Workload Resource Efficiency","Container-level CPU/memory use, exact units, resource configuration and actionable saturation risks.",panels,rows,variables,True)


def platform_dashboard():
    c='cluster_name=~"${platform_cluster}"'
    nodekeys="cluster_name,node"
    fskeys="cluster_name,node,device,mountpoint,fstype"
    fs=f'{c},job="sre-node",device!~"/dev/loop[0-9]+",fstype!~"tmpfs|overlay|squashfs",mountpoint!~"/var/lib/kubelet/.*"'
    size=f'max by ({fskeys}) (node_filesystem_size_bytes{{{fs}}})'
    free=f'max by ({fskeys}) (node_filesystem_free_bytes{{{fs}}})'
    avail=f'max by ({fskeys}) (node_filesystem_avail_bytes{{{fs}}})'
    used=f'({size}) - ({free})'
    # df uses used / (used + available), excluding reserved blocks from the denominator.
    ratio=f'({used}) / clamp_min(({used}) + ({avail}), 1)'
    fa="${cluster_name} · ${node} · ${mountpoint} · ${device}"
    pk="cluster_name,namespace,persistentvolumeclaim"
    pc=f'{c},namespace=~"${{platform_namespace}}"'
    inodes=f'max by ({pk}) (kubernetes_kubelet_volume_stats_inodes{{{pc}}})'
    def pvc(suffix):
        return f'max by ({pk}) (kubernetes_kubelet_volume_stats_{suffix}{{{pc}}}) and on ({pk}) ({inodes} > 0)'
    cap,pu,pav=pvc("capacity_bytes"),pvc("used_bytes"),pvc("available_bytes")
    pa="${cluster_name} · ${namespace} · ${persistentvolumeclaim}"
    present=f'max by ({nodekeys}) (kubernetes_state_node_age{{{c}}} * 0 + 1)'
    collected=f'max by ({nodekeys}) (up{{{c},job="sre-node"}} == 1)'
    bad=f'max by (cluster_name,namespace,pod_name,pod_phase) (last_over_time(kubernetes_state_pod_status_phase{{{pc},pod_phase!~"Running|Succeeded"}}[5m] @ end()) == 1)'
    badnames=f'label_join({bad}, "item", " · ", "cluster_name", "namespace", "pod_name", "pod_phase")'
    panels={
      "guide":markdown("Scope and interpretation", "Cluster filters apply to every panel. Namespace applies to pods, workloads and PVCs; node, PV and etcd panels are cluster-scoped. **Filesystem rows identify the mount and device**; they are never summed across overlay/bind mounts. Used = size − free; availability excludes reserved blocks. Utilization matches `df`: used / (used + available). **PVC filesystem usage requires inode telemetry > 0.** Raw block devices and absent CSI statistics are listed as unmeasured, never as 100% full or 0% used. etcd now uses member metrics; voting topology alone is not a health check. Warning/critical thresholds live in the monitors, with durations and runbooks, rather than unnamed chart lines."),
      "ready":stat("Nodes Ready", "Ready conditions divided by the inventory of nodes. This says nothing about absent collectors.",f'sum(kubernetes_state_node_by_condition{{{c},condition="Ready",status="true"}}) / count({present})',"percentunit",0),
      "coverage":stat("Node OS collection coverage", "Healthy sre-node targets / inventoried nodes. 100% is required before interpreting missing resource series.",f'count({collected}) / count({present})',"percentunit",0),
      "nonRunning":stat("Pods outside Running / Succeeded", "Current phase at the selected end time. Pending is not always a failure; the monitor requires persistence.",f'(sum({bad})) or (sum(kubernetes_state_pod_status_phase{{{pc}}}) * 0)',"none",0,BLUE,"Pods"),
      "nonRunningList":series_table("Current pod exceptions · phase and namespace", "The table lists current pod exceptions, without numeric flags or unnamed thresholds.",named_empty(badnames,"No current phase exceptions (verify collection)"),"${item}",values=False),
      "restarts":series_table("Container restarts in the last hour", "All positive one-hour increases by cluster, namespace, pod and container. Empty means no observed increase; verify coverage. Monitor: repeated restarts >= 3 / 15m sustained for 5m.",f'max by (cluster_name,namespace,pod_name,container) (increase(kubernetes_state_container_restarts{{{pc}}}[1h])) > 0',"${cluster_name} · ${namespace} · ${pod_name} · ${container}","none",0),
      "availability":timeseries("Unavailable workload replicas", "Replica deficit by cluster and namespace; investigate persistence beyond deployment rollout windows.",[
        query("Deployment · ${cluster_name} · ${namespace}",f'sum by (cluster_name,namespace) (kubernetes_state_deployment_replicas_unavailable{{{pc}}})'),
        query("DaemonSet · ${cluster_name} · ${namespace}",f'sum by (cluster_name,namespace) (kubernetes_state_daemonset_daemons_unavailable{{{pc}}})'),
        query("StatefulSet · ${cluster_name} · ${namespace}",f'clamp_min(sum by (cluster_name,namespace) (kubernetes_state_statefulset_replicas_desired{{{pc}}}) - sum by (cluster_name,namespace) (kubernetes_state_statefulset_replicas_ready{{{pc}}}), 0)')],"none",0),
      "filesystem":series_table("Node filesystem utilization · matches df", "Each row retains cluster, node, mountpoint, device and filesystem. Monitors use available bytes and a persistence window; there are no unnamed threshold lines.",ratio,fa,"percentunit",2),
      "nodeUsed":series_table("Filesystem used", "Size minus free, per mount; includes the Harvester data disk. Values are not rootfs-only and not sums across devices.",used,fa,"bytes(IEC)",2),
      "nodeTotal":series_table("Filesystem capacity", "Physical filesystem size per mount; separate from block device, virtual disk and PVC requested capacity.",size,fa,"bytes(IEC)",2),
      "nodeFree":series_table("Filesystem available to applications", "Available excludes filesystem-reserved blocks; this can differ from the free counter.",avail,fa,"bytes(IEC)",2),
      "inodeRisk":series_table("Filesystem inode utilization", "Inode exhaustion can fail writes even when free bytes remain.",f'1 - max by ({fskeys}) (node_filesystem_files_free{{{fs}}}) / (max by ({fskeys}) (node_filesystem_files{{{fs}}}) > 0)',fa,"percentunit",2),
      "pvcRisk":series_table("Measured PVC filesystem utilization", "Only claims with positive inode telemetry. Unmeasured and raw block claims are listed separately.",f'({pu}) / ({cap})',pa,"percentunit",2),
      "pvcUsed":series_table("Measured PVC filesystem used", "CSI / kubelet bytes used inside filesystem volumes; not physical Longhorn replica space or guest filesystem usage inside a block volume.",pu,pa,"bytes(IEC)",2),
      "pvcCapacity":series_table("Measured PVC filesystem capacity", "Filesystem capacity may be smaller than PVC requested size because of formatting and metadata.",cap,pa,"bytes(IEC)",2),
      "pvcAvailable":series_table("Measured PVC filesystem available", "Space available inside the measured filesystem; exclude block-device statistics.",pav,pa,"bytes(IEC)",2),
      "pvcUnmeasured":series_table("PVCs without filesystem usage · includes raw block", "Inventory minus claims with positive inode telemetry. These claims need guest metrics, CSI support, attachment or a filesystem; absence is not healthy zero.",f'label_join((max by ({pk}) (kubernetes_state_persistentvolumeclaim_request_storage{{{pc}}})) unless on ({pk}) ({inodes} > 0), "item", " · ", "cluster_name", "namespace", "persistentvolumeclaim")',"${item}",values=False),
      "pvPhases":series_table("PersistentVolume phases · cluster scope", "All PVs with their current phase and storage class. Released is not automatically a failure: inspect reclaim policy and data ownership.",f'label_join(max by (cluster_name,persistentvolume,phase,storageclass) (last_over_time(kubernetes_state_persistentvolume_by_phase{{{c}}}[5m] @ end()) == 1), "item", " · ", "cluster_name", "persistentvolume", "phase", "storageclass")',"${item}",values=False),
      "pvcPhases":series_table("PersistentVolumeClaim phases", "All claims with current namespace, phase and storage class.",f'label_join(max by (cluster_name,namespace,persistentvolumeclaim,phase,storageclass) (last_over_time(kubernetes_state_persistentvolumeclaim_status{{{pc}}}[5m] @ end()) == 1), "item", " · ", "cluster_name", "namespace", "persistentvolumeclaim", "phase", "storageclass")',"${item}",values=False),
      "nodeMissing":series_table("Nodes missing OS telemetry", "Inventoried nodes without a healthy node-exporter target. Missing data never proves resource health.",named_empty(f'label_join(({present}) unless on ({nodekeys}) ({collected}), "item", " · ", "cluster_name", "node")',"All inventoried nodes have an OS target"),"${item}",values=False),
    }
    ea="${cluster_name} · ${node}"
    e=f'{c},job="sre-etcd"'
    etcd_panels=[
      ("etcdLeader","etcd member has leader",f'max by ({nodekeys}) (etcd_server_has_leader{{{e}}})',"none",0,"1 means this member can see a leader; 0 means no leader. Missing telemetry remains absent."),
      ("etcdLeaderChanges","etcd leader changes · rolling 1h",f'max by ({nodekeys}) (increase(etcd_server_leader_changes_seen_total{{{e}}}[1h]))',"none",0,"Changes seen by each member; do not sum the same election across members."),
      ("etcdPending","etcd pending Raft proposals",f'max by ({nodekeys}) (etcd_server_proposals_pending{{{e}}})',"none",0,"Proposals queued for commit; sustained growth can indicate disk/network saturation or loss of quorum."),
      ("etcdApplyLag","etcd committed minus applied proposals",f'clamp_min(max by ({nodekeys}) (etcd_server_proposals_committed_total{{{e}}}) - max by ({nodekeys}) (etcd_server_proposals_applied_total{{{e}}}), 0)',"none",0,"Per-member application backlog. These total-named metrics are gauges; do not apply rate() to this difference."),
      ("etcdFailed","etcd failed proposals · rolling 15m",f'max by ({nodekeys}) (increase(etcd_server_proposals_failed_total{{{e}}}[15m]))',"none",0,"Failed consensus proposals; correlate elections, peer RTT and quorum."),
      ("etcdWAL","etcd WAL fsync p99 · seconds",f'histogram_quantile(0.99, sum by (cluster_name,node,le) (rate(etcd_disk_wal_fsync_duration_seconds_bucket{{{e}}}[5m])))',"seconds",4,"Disk WAL fsync latency over 5m. Investigate sustained p99 above 10 ms."),
      ("etcdCommit","etcd backend commit p99 · seconds",f'histogram_quantile(0.99, sum by (cluster_name,node,le) (rate(etcd_disk_backend_commit_duration_seconds_bucket{{{e}}}[5m])))',"seconds",4,"Backend transaction latency over 5m. Investigate sustained p99 above 25 ms."),
      ("etcdDB","etcd database / quota",f'max by ({nodekeys}) (etcd_mvcc_db_total_size_in_bytes{{{e}}}) / max by ({nodekeys}) (etcd_server_quota_backend_bytes{{{e}}})',"percentunit",2,"Physical backend database / quota. Approaching the quota risks NOSPACE alarms; follow snapshot, compaction and safe defragmentation procedures."),
      ("etcdScrape","etcd metrics target status",f'min by ({nodekeys}) (up{{{c},job="sre-etcd"}})',"none",0,"1 = scrape succeeded, 0 = failed. Compare member count against expected topology; scrape health is not consensus health."),
    ]
    for key,title,expr,unit,dec,desc in etcd_panels:panels[key]=series_table(title,desc,expr,ea,unit,dec)
    panels["etcdPeer"]=series_table("etcd peer RTT p99 · seconds", "Round-trip latency to each peer. A single-member cluster has no peer series; this is expected and is not a zero-latency claim.",f'histogram_quantile(0.99, sum by (cluster_name,node,To,le) (rate(etcd_network_peer_round_trip_time_seconds_bucket{{{e}}}[5m])))',"${cluster_name} · ${node} → ${To}","seconds",4)
    for key,title,expr,unit,desc in [
        ("hostCPU","Host CPU busy · all logical CPUs",'1 - avg by (cluster_name,node) (rate(node_cpu_seconds_total{'+c+',job="sre-node",mode="idle"}[5m]))',"percentunit","CPU occupied across logical cores; compare saturation with workload latency."),
        ("hostMemory","Host OS available memory",'max by (cluster_name,node) (node_memory_MemAvailable_bytes{'+c+',job="sre-node"}) / max by (cluster_name,node) (node_memory_MemTotal_bytes{'+c+',job="sre-node"})',"percentunit","MemAvailable / MemTotal from the operating system, not Kubernetes requests."),
        ("ioPressure","Host I O stall pressure",'max by (cluster_name,node) (rate(node_pressure_io_waiting_seconds_total{'+c+',job="sre-node"}[5m]))',"percentunit","Linux PSI time with at least one task stalled on IO. Missing means kernel collector support must be checked."),
        ("memoryPressure","Host memory stall pressure",'max by (cluster_name,node) (rate(node_pressure_memory_waiting_seconds_total{'+c+',job="sre-node"}[5m]))',"percentunit","Linux PSI memory stalls; useful before an OOM and alongside application latency.")
    ]:panels[key]=series_table(title,desc,expr,ea,unit,2)
    for key,title,source in [('cpuGauge','Busiest server CPU','hostCPU'),('memoryGauge','Most used server memory','hostMemory'),('diskGauge','Most used host filesystem','filesystem')]:
        source_query=panels[source]['spec']['queries'][0]['spec']['plugin']['spec']['query']
        if key=='memoryGauge':source_query=f'1 - ({source_query})'
        panels[key]=utilization_gauge(title,'Highest utilization at the selected end, with the affected server or filesystem. The namespace filter does not apply. Orange starts at 80%, red at 90%; compare duration and the detailed charts.',source_query,fa if key=='diskGauge' else ea)
    panels["networkErrors"]=series_table("Host network errors · packets per second","Receive plus transmit errors by interface. Correlate drops, retransmits and link state; virtual interfaces remain identifiable.", 'sum by (cluster_name,node,device) (rate(node_network_receive_errs_total{'+c+',job="sre-node",device!="lo"}[5m]) + rate(node_network_transmit_errs_total{'+c+',job="sre-node",device!="lo"}[5m]))',"${cluster_name} · ${node} · ${device}","none",3)
    panels['etcdGuide']=markdown('How to read etcd', '**etcd stores Kubernetes state.** A member is a server that keeps a copy. A working metrics endpoint and a recognized leader are separate checks. **Peer RTT applies only when other members exist**; no peer chart is expected on a single-member cluster. p99 means 99 out of 100 operations completed within the displayed time; lower is better. WAL flush time above 10 ms or database commit time above 25 ms for five minutes needs investigation. These are initial thresholds, not an SLA guarantee.')
    panels['collectorQueue']=series_table('Metrics waiting for delivery', 'Bytes waiting to reach SUSE. Small peaks are normal; persistent growth suggests a receiver, DNS, or network problem. The series disappears if all delivery stops.', f'max by (cluster_name,node,collector_kind) (vmagent_remotewrite_pending_data_bytes{{{c},job="sre-collector"}})', '${cluster_name} · ${node} · ${collector_kind}', 'bytes(IEC)',2)
    panels['collectorRetries']=series_table('Delivery retries in 15 minutes', 'Additional attempts after a failure. Zero is expected during stable operation. Logs distinguish DNS, TLS, and HTTP 503 failures.', f'max by (cluster_name,node,collector_kind) (increase(vmagent_remotewrite_retries_count_total{{{c},job="sre-collector"}}[15m]))', '${cluster_name} · ${node} · ${collector_kind}', 'none',0)
    variables=[variable("platform_cluster","Cluster","cluster_name","kubernetes_state_node_count","One or more clusters."),variable("platform_namespace","Namespace (workloads / PVCs)","namespace",'kubernetes_state_pod_status_phase{cluster_name=~"${platform_cluster}"}',"Applies to workload and PVC panels; nodes, PVs and etcd remain cluster-scoped.")]
    rows=[row(2,"ready","coverage","nonRunning"),row(2,"nonRunningList"),row(3,"availability","restarts"),row(3,"filesystem"),row(3,"nodeUsed","nodeTotal"),row(3,"nodeFree","inodeRisk"),row(3,"pvcRisk","pvcUsed"),row(3,"pvcCapacity","pvcAvailable"),row(2,"pvcUnmeasured"),row(3,"pvPhases","pvcPhases"),row(2,"nodeMissing"),row(3,"hostCPU","hostMemory"),row(3,"ioPressure","memoryPressure"),row(3,"networkErrors"),row(3,"etcdLeader","etcdScrape"),row(3,"etcdLeaderChanges","etcdFailed"),row(3,"etcdPending","etcdApplyLag"),row(3,"etcdWAL","etcdCommit"),row(3,"etcdPeer","etcdDB")]
    rows.insert(1,row(2,'cpuGauge','memoryGauge','diskGauge'))
    rows.insert(next(i for i,r in enumerate(rows) if 'etcdLeader' in r['keys']),row(2,'etcdGuide'))
    rows.append(row(3,'collectorQueue','collectorRetries'))
    return dashboard("Kubernetes Platform Health","Verified node filesystems, PVC coverage, current exceptions and native etcd consensus signals.",panels,rows,variables,True)

def traefik_dashboard():
    c='cluster_name=~"${ingress_cluster}"'
    inventory=f'max by (cluster_name,namespace,service,backend) (label_replace(label_join(label_replace(kubernetes_state_ingress_path{{{c},namespace=~"${{ingress_namespace}}",service=~"${{ingress_service}}"}}, "backend", "$1", "service", "(.*)"), "service_key", "-", "namespace", "service", "kube_service_port"), "service", "$1@kubernetes", "service_key", "(.*)"))'
    inventory=f'(max by (cluster_name,namespace,service,backend) (label_replace(sre_ingress_backend_info{{{c},ingress_namespace!="",ingress_namespace=~"${{ingress_namespace}}",backend=~"${{ingress_service}}"}}, "namespace", "$1", "ingress_namespace", "(.*)"))) or (({inventory}) unless on (cluster_name) (sre_ingress_inventory_success{{{c}}}))'
    scoped=lambda metric: f'({metric}) * on (cluster_name,service) group_left(namespace,backend) ({inventory})'
    http=f'cluster_name=~"${{ingress_cluster}}",protocol="http"'
    def counter(raw, agent, selector, operation, window, labels):
        raw_query=f'max by (cluster_name,instance,service,protocol,code,method,le) ({operation}({raw}{{{selector}}}[{window}]))'
        agent_query=f'label_replace({operation}({agent}{{{selector},traefik_backend!=""}}[{window}]), "service", "$1", "traefik_backend", "(.*)")'
        return f'sum by ({",".join(labels)}) (({raw_query}) or (({agent_query}) unless on (cluster_name) ({raw_query})))'
    request_labels=["cluster_name","service","protocol","code","method"]
    rate5m=scoped(counter("traefik_service_requests_total","_traefik_service_requests",http,"rate","5m",request_labels))
    recent_rate=scoped(counter("traefik_service_requests_total","_traefik_service_requests",http,"irate","2m",request_labels))
    duration_sum=scoped(counter("traefik_service_request_duration_seconds_sum","_traefik_service_request_duration_seconds_sum",http,"rate","5m",request_labels))
    duration_count=scoped(counter("traefik_service_request_duration_seconds_count","_traefik_service_request_duration_seconds_count",http,"rate","5m",request_labels))
    mean_latency=f"sum({duration_sum}) / (sum({duration_count}) > 0)"
    inc1h=scoped(counter("traefik_service_requests_total","_traefik_service_requests",http,"increase","1h",request_labels))
    inc24h=scoped(counter("traefik_service_requests_total","_traefik_service_requests",http,"increase","24h",request_labels))
    clients1h=scoped(counter("traefik_service_requests_total","_traefik_service_requests",f'{http},code=~"4.."',"increase","1h",request_labels))
    errors1h=scoped(counter("traefik_service_requests_total","_traefik_service_requests",f'{http},code=~"5.."',"increase","1h",request_labels))
    buckets=scoped(counter("traefik_service_request_duration_seconds_bucket","_traefik_service_request_duration_seconds_bucket",http,"rate","5m",request_labels+["le"]))
    buckets1h=scoped(counter("traefik_service_request_duration_seconds_bucket","_traefik_service_request_duration_seconds_bucket",http,"increase","1h",request_labels+["le"]))
    by_backend_1h=f'sum by (cluster_name,namespace,backend) ({inc1h})'
    by_backend_24h=f'sum by (cluster_name,namespace,backend) ({inc24h})'
    # Traefik creates status-code series only after an outcome is observed.
    # An absent error series is zero only when the same selected traffic exists.
    by_backend_errors=f'(sum by (cluster_name,namespace,backend) ({errors1h}) or (({by_backend_1h}) * 0)) / (({by_backend_1h}) > 0)'
    panels={
      "guide":markdown("Ingress signals without application instrumentation", "These metrics come from Traefik, so the application does **not** need an SDK. Select **Application / Service** to isolate a benchmark or workload; otherwise high-volume Services can hide small changes in namespace totals. **Ingress namespace** lists only namespaces that own an Ingress in the selected cluster; namespaces without an Ingress are intentionally absent because they cannot produce Traefik service traffic. Request totals use rolling windows, bounded by collected history, and are rounded to a request. A 24h window does not prove 24h of uninterrupted collection. Health checks such as /healthz ARE included by Traefik; these are HTTP calls, not people or business transactions. Counts use the native None unit and show every digit. Hover the `?` icon for the SUSE widget tooltip; essential interpretation is also kept visible here. Instrument the application only for internal routes, exceptions, dependencies, traces or business operations."),
      "rps":stat("Selected services throughput · 5m","Current HTTP request rate for all Services in the selected namespace.",f'sum({rate5m})',"reqps",2,BLUE,"Requests/s"),
      "rpsRecent":stat("Requests per second", "Rate across the latest two collected samples.",f"sum({recent_rate})","reqps",2,BLUE,"Recent requests/s"),
      "meanLatency":stat("Application latency", "Request-weighted mean measured by Traefik over five minutes.",mean_latency,"seconds",3,BLUE,"Mean latency"),
      "requestRate":timeseries("Requests per second", "Compare recent sample intervals with the five-minute average.",[query("Latest sample interval",f"sum({recent_rate})"),query("Five-minute average",f"sum({rate5m})")],"reqps",2),
      "requests1h":stat("Selected services requests · rolling 1h","Rounded completed HTTP requests in the last rolling hour.",f'round(sum({inc1h}), 1)',"decimal",0,BLUE,"Requests"),
      "requests24h":stat("Selected services requests · rolling 24h","Rounded completed HTTP requests in the last rolling 24 hours.",f'round(sum({inc24h}), 1)',"decimal",0,PURPLE,"Requests"),
      "client4xx":stat("4xx responses · rolling 1h","Rounded client-error responses in the last rolling hour. A 4xx usually indicates invalid, unauthorized or missing client requests; expected authentication responses should be interpreted in context.",f'round((sum({clients1h}) or (sum({inc1h}) * 0)), 1)',"none",0,GREEN,"4xx",[{"color":AMBER,"value":1},{"color":RED,"value":100}]),
      "error5xx":stat("5xx responses · rolling 1h","Rounded server-error responses in the last rolling hour. Any non-zero value deserves correlation with the affected Service.",f'round((sum({errors1h}) or (sum({inc1h}) * 0)), 1)',"none",0,GREEN,"5xx",[{"color":AMBER,"value":1},{"color":RED,"value":10}]),
      "p95":stat("Selected application p95 · 1h","95% of requests observed by Traefik in the rolling hour completed at or below this duration. It remains visible after a short benchmark finishes.",f'histogram_quantile(0.95, sum by (le) ({buckets1h}))',"seconds",3,GREEN,"p95",[{"color":AMBER,"value":0.5},{"color":RED,"value":1.0}]),
      "serviceCount":stat("Services receiving traffic","Number of selected backend Services with traffic in the last hour.",f'count(({by_backend_1h}) > 0)',"none",0,BLUE,"Services"),
      "serviceRequests1h":multistat("Requests by Service · rolling 1h","Rounded rolling one-hour request total for each backend.",f'topk(10, round({by_backend_1h}, 1))',"decimal",0,BLUE,alias="${cluster_name} · ${namespace} · ${backend}"),
      "serviceRequests24h":multistat("Requests by Service · rolling 24h","Rounded rolling 24-hour request total for each backend.",f'topk(10, round({by_backend_24h}, 1))',"decimal",0,PURPLE,alias="${cluster_name} · ${namespace} · ${backend}"),
      "serviceErrorRatio":multistat("5xx rate by Service · 1h","Error ratio per backend. Amber from 1%; red from 5%.",f'topk(10, {by_backend_errors})',"percentunit",2,GREEN,alias="${cluster_name} · ${namespace} · ${backend}",steps=[{"color":AMBER,"value":0.01},{"color":RED,"value":0.05}]),
      "serviceTraffic":timeseries("Requests/s by Service","Compare live throughput among backend Services.",[query("${cluster_name} · ${namespace} · ${backend}",f'sum by (cluster_name,namespace,backend) ({rate5m})')],"reqps",2),
      "byCode":timeseries("HTTP responses by status code","Per-second response rate by HTTP code for selected Services.",[query("HTTP ${code}",f'sum by (code) ({rate5m})')],"reqps",2),
      "byMethod":timeseries("HTTP requests by method","Per-second request rate split by GET, POST, PUT, PATCH, DELETE and other observed methods.",[query("${method}",f'sum by (method) ({rate5m})')],"reqps",2),
      "latency":timeseries("Selected services latency","p50, p95 and p99 across selected backend Services.",[
          query("Mean",mean_latency),
          query("p50",f'histogram_quantile(0.50, sum by (le) ({buckets}))'),
          query("p95",f'histogram_quantile(0.95, sum by (le) ({buckets}))'),
          query("p99",f'histogram_quantile(0.99, sum by (le) ({buckets}))')],"seconds",3,[{"color":AMBER,"value":0.5},{"color":RED,"value":1.0}]),
      "serviceLatency":timeseries("p95 latency by Service","Identify the backend with the slowest ingress-observed response.",[query("${cluster_name} · ${namespace} · ${backend}",f'histogram_quantile(0.95, sum by (cluster_name,namespace,backend,le) ({buckets}))')],"seconds",3),
      "bandwidth":timeseries("Payload bandwidth by selected Services","Request and response payload bytes per second.",[
          query("Request bytes/s",f'sum({scoped(counter("traefik_service_requests_bytes_total","_traefik_service_requests_bytes",http,"rate","5m",["cluster_name","service","protocol"]))})'),
          query("Response bytes/s",f'sum({scoped(counter("traefik_service_responses_bytes_total","_traefik_service_responses_bytes",http,"rate","5m",["cluster_name","service","protocol"]))})')],"Bps",1),
      "tlsExpiry":multistat("TLS certificate expiry","Days until each unique certificate expires, deduplicated across Traefik replicas. The label shows cluster and certificate SAN. Red below 7 days; amber below 30.",f'sort((max by (cluster_name,sans,serial) ((traefik_tls_certs_not_after{{{c}}}) or (_traefik_tls_certs_not_after{{{c}}})) - time()) / 86400)',"decimal",0,RED,alias="${cluster_name} · ${sans}",steps=[{"color":AMBER,"value":7},{"color":GREEN,"value":30}])
    }
    for key in ["serviceRequests1h","serviceRequests24h","serviceErrorRatio"]:
        old=panels[key]["spec"]
        expr=old["queries"][0]["spec"]["plugin"]["spec"]["query"]
        fmt=old["plugin"]["spec"]["format"]
        panels[key]=series_table(old["display"]["name"],old["display"]["description"],expr,"${cluster_name} · ${namespace} · ${backend}",fmt["unit"],fmt["decimalPlaces"])
    panels["tlsExpiry"]=series_table("TLS certificates · days remaining (cluster scope)", "One row per certificate SAN and serial, deduplicated across replicas. Cluster-scoped: certificate SANs can span several namespaces/services. Earliest replica expiration is retained. Negative days means expired.",f'(min by (cluster_name,sans,serial) ((traefik_tls_certs_not_after{{{c}}}) or (_traefik_tls_certs_not_after{{{c}}})) - time()) / 86400',"${cluster_name} · ${sans} · serial ${serial}","none",2)
    panels["openConnections"]=series_table("Traefik open connections · cluster scope", "Current open proxy connections by entrypoint, including long-lived websocket connections. Not filtered by backend service.",f'sum by (cluster_name,entrypoint) ((traefik_open_connections{{{c}}}) or ((_traefik_open_connections{{{c}}}) unless on (cluster_name) (traefik_open_connections{{{c}}})))',"${cluster_name} · ${entrypoint}","none",0)
    panels["codeTotals"]=series_table("Completed responses by code · rolling 24h", "Auditable distribution of the full day total. Code 0 is a proxy/connection outcome, not an HTTP success code. Retries and websocket lifetimes can affect interpretation.",f'round(sum by (cluster_name,namespace,backend,code,method) ({inc24h}), 1)',"${cluster_name} · ${namespace} · ${backend} · ${code} · ${method}","none",0)
    error_rate=scoped(counter("traefik_service_requests_total","_traefik_service_requests",f'{http},code=~"4..|5.."',"rate","5m",request_labels))
    panels['errorTimeline']=timeseries('HTTP errors over time by application and code','Locate the affected application and time window. A point averages five minutes, not one failed request. Exact paths, times and causes require access logs, application logs or traces.',[query('${cluster_name} · ${namespace} · ${backend} · HTTP ${code}',f'sum by (cluster_name,namespace,backend,code) ({error_rate})')],'reqps',3,legend='bottom')
    raw_backend='sum by (cluster_name,service) ((traefik_service_requests_total{'+http+'}) or (label_replace(_traefik_service_requests{'+http+',traefik_backend!=""}, "service", "$1", "traefik_backend", "(.*)") unless on (cluster_name) traefik_service_requests_total{'+http+'}))'
    panels["backendRaw"]=series_table("Raw backend counters · current processes", "Current per-instance counters. Resets on process restart; does not count unique users. Compare with access logs and rolling increase.",f'sum by (cluster_name,namespace,backend) ({scoped(raw_backend)})',"${cluster_name} · ${namespace} · ${backend}","none",0)
    variables=[
      variable("ingress_cluster","Cluster","cluster_name",'{__name__=~"traefik_service_requests_total|_traefik_service_requests"}',"Cluster with validated Traefik request metrics."),
      variable("ingress_namespace","Ingress namespace","namespace",'kubernetes_state_ingress_path{cluster_name=~"${ingress_cluster}",service!=""}',"Only namespaces that own at least one Kubernetes Ingress in the selected cluster."),
      variable("ingress_service","Application / Service","service",'kubernetes_state_ingress_path{cluster_name=~"${ingress_cluster}",namespace=~"${ingress_namespace}"}',"Kubernetes Service reached through Ingress. Select one to isolate its traffic, errors and latency.")
    ]
    history = '({__name__=~"traefik_service_requests_total|_traefik_service_requests",cluster_name=~"${ingress_cluster}"})'
    panels["history"]=stat("Oldest selected-cluster counter sample · hours", "Approximate age of the oldest Traefik counter sample in 24h, evaluated every minute. This is an upper bound on usable history, not proof of uninterrupted coverage. Never extrapolate it to daily demand.", 'clamp_max((time() - min(min_over_time(timestamp(' + history[1:-1] + ')[24h:1m]))) / 3600, 24)', "none", 2, BLUE, "Hours observed · maximum 24")
    rows=[row(2,"rps","rpsRecent"),row(2,"meanLatency","p95"),row(3,"requestRate"),row(3,"latency"),row(2,"requests1h","requests24h"),row(2,"client4xx","error5xx"),row(3,"errorTimeline"),row(2,"serviceCount","openConnections","history"),row(3,"tlsExpiry"),row(3,"serviceRequests1h","serviceRequests24h"),row(3,"serviceTraffic","serviceErrorRatio"),row(3,"byCode","serviceLatency"),row(3,"bandwidth","backendRaw"),row(3,"codeTotals")]
    return dashboard("Traefik Ingress Health","Traefik traffic, errors and latency correlated to Kubernetes namespaces and backend Services.",panels,rows,variables,True)

def harvester_dashboard():
    v='k8s_cluster_name=~"${vm_cluster}",namespace=~"${vm_namespace}",name=~"${vm_name}"'
    vk="k8s_cluster_name,namespace,name"
    a="${k8s_cluster_name} · ${namespace} · ${name}"
    running=f'max by ({vk}) (kubevirt_vmi_info{{{v},phase="running"}})'
    def metric(name, extra=""):
        return f'max by ({vk}) ({name}{{{v}{extra}}}) and on ({vk}) ({running})'
    cpu_domain_request=metric("kubevirt_vm_resource_requests",',resource="cpu",unit="cores",source="requests"')
    total=metric("kubevirt_vmi_memory_available_bytes")
    available=metric("kubevirt_vmi_memory_usable_bytes")
    used=f'clamp_min(({total}) - ({available}), 0)'
    hv='cluster_name=~"${vm_cluster}",job="sre-node"'
    hk="cluster_name,node"
    virtualization_clusters='max by (cluster_name) (label_replace(up{service_name="kubevirt-metrics",k8s_cluster_name=~"${vm_cluster}"}, "cluster_name", "$1", "k8s_cluster_name", "(.*)") or label_replace(kubevirt_vmi_info{k8s_cluster_name=~"${vm_cluster}"}, "cluster_name", "$1", "k8s_cluster_name", "(.*)"))'
    hosttotal=f'max by ({hk}) (node_memory_MemTotal_bytes{{{hv}}}) and on (cluster_name) ({virtualization_clusters})'
    hostavail=f'max by ({hk}) (node_memory_MemAvailable_bytes{{{hv}}}) and on (cluster_name) ({virtualization_clusters})'
    panels={
      "guide":markdown("VM, guest and host are different layers", "**Guest OS use = guest MemTotal − MemAvailable**, from KubeVirt available/usable balloon statistics, in bytes. KubeVirt `available_bytes` is total guest memory; `usable_bytes` is the available estimate. QEMU RSS and virt-launcher working set measure host consumption and include overhead. VM **domain requests** and **domain limits** are read separately; guest memory/vCPU configuration is not the request. Missing guest-agent / balloon data is unknown, not zero. Guest filesystem data comes from QEMU Guest Agent; raw block PVC capacity is not guest disk usage. Host panels are cluster-scoped, independent of VM/namespace filters. Filesystem and OS memory of monitored guests can also be verified in Kubernetes Platform Health."),
      "guestUsed":series_table("Guest OS memory used · total minus available", "Guest balloon statistics; comparable to Linux free used=total-available. Cached reclaimable memory is not counted as pressure.",used,a,"bytes(IEC)",2),
      "guestAvailable":series_table("Guest OS available memory", "Memory that the guest estimates can be used without swapping; not the guest total despite KubeVirt's available/usable naming.",available,a,"bytes(IEC)",2),
      "guestTotal":series_table("Guest OS total memory", "Guest-visible total reported by balloon statistics; may be smaller than the configured guest memory due to reserved regions.",total,a,"bytes(IEC)",2),
      "domainRequest":series_table("VM domain memory request", "Scheduling reservation from domain resources.requests.memory; source=domain prevents confusing it with source=guest.",metric("kubevirt_vm_resource_requests",',resource="memory",unit="bytes",source="domain"'),a,"bytes(IEC)",2),
      "domainLimit":series_table("VM domain memory limit", "Configured domain resources.limits.memory; distinct from the virt-launcher container ceiling including KubeVirt overhead.",metric("kubevirt_vm_resource_limits",',resource="memory",unit="bytes"'),a,"bytes(IEC)",2),
      "configuredGuest":series_table("Configured guest memory", "Domain guest memory assigned to the VM; not a scheduling request.",metric("kubevirt_vm_resource_requests",',resource="memory",unit="bytes",source="guest"'),a,"bytes(IEC)",2),
      "resident":series_table("QEMU resident memory on host", "Resident memory of the VM process on the host. This is not application use inside the guest OS.",metric("kubevirt_vmi_memory_resident_bytes"),a,"bytes(IEC)",2),
      "vcpuUse":series_table("VM CPU use (vCPU cores)", "Rate of guest VM CPU seconds over five minutes; one core=1000mCPU. I/O wait and steal need separate guest metrics.",f'sum by ({vk}) (rate(kubevirt_vmi_cpu_usage_seconds_total{{{v}}}[5m]))',a,"none",3),
      "vcpuRequest":series_table("VM domain CPU request (mCPU)", "Scheduling request from domain.resources.requests.cpu. CPU source=requests is required; CPU source=domain describes the guest topology, unlike the memory source label.",f'({cpu_domain_request}) * 1000',a,"none",1),
      "vcpuLimit":series_table("VM domain CPU limit (vCPU cores)", "Configured CPU ceiling in cores, not millicores.",metric("kubevirt_vm_resource_limits",',resource="cpu",unit="cores"'),a,"none",2),
      "hostUsed":series_table("Harvester host OS memory used", "Host MemTotal − MemAvailable from node-exporter. Includes virtual machines and host services, not just Kubernetes pod requests.",f'({hosttotal}) - ({hostavail})',"${cluster_name} · ${node}","bytes(IEC)",2),
      "hostAvailable":series_table("Harvester host OS available memory", "Host Linux MemAvailable; independent of VM selection.",hostavail,"${cluster_name} · ${node}","bytes(IEC)",2),
      "hostRequests":series_table("Harvester pod memory requests", "Scheduling reservations summed across regular containers on the Harvester host, including virt-launcher. This is reserved capacity, not OS use.",f'sum by (cluster_name) (kubernetes_state_container_memory_requested{{cluster_name=~"${{vm_cluster}}"}}) and on (cluster_name) ({virtualization_clusters})',"${cluster_name}","bytes(IEC)",2),
      "hostLimits":series_table("Harvester pod memory limits", "Sum of configured memory limits; missing limits are not zero ceilings and overcommit is possible.",f'sum by (cluster_name) (kubernetes_state_container_memory_limit{{cluster_name=~"${{vm_cluster}}"}}) and on (cluster_name) ({virtualization_clusters})',"${cluster_name}","bytes(IEC)",2),
      "guestMissing":series_table("Running VMs without guest memory statistics", "Running VM inventory minus usable+total guest statistics. Install/configure guest balloon driver; QEMU Guest Agent additionally enables filesystem and OS identity data.",named_empty(f'label_join(({running}) unless on ({vk}) (({total}) and on ({vk}) ({available})), "item", " · ", "k8s_cluster_name", "namespace", "name")',"Every running VM has guest memory statistics"),"${item}",values=False)
    }
    fskeys=vk+",disk_name,mount_point,file_system_type"
    fu=f'max by ({fskeys}) (kubevirt_vmi_filesystem_used_bytes{{{v},disk_name!~"(/dev/)?loop[0-9]+",file_system_type!~"tmpfs|overlay|squashfs"}})'
    fc=f'max by ({fskeys}) (kubevirt_vmi_filesystem_capacity_bytes{{{v},disk_name!~"(/dev/)?loop[0-9]+",file_system_type!~"tmpfs|overlay|squashfs"}})'
    fa=a+" · ${mount_point} · ${disk_name}"
    panels["guestDiskUsed"]=series_table("Guest filesystem used", "QEMU Guest Agent reports bytes used on each mounted guest filesystem. Do not sum bind mounts or compare this with raw PVC allocation.",fu,fa,"bytes(IEC)",2)
    panels["guestDiskCapacity"]=series_table("Guest filesystem capacity", "Guest-agent filesystem capacity; df and statvfs can differ slightly in reserved metadata accounting.",fc,fa,"bytes(IEC)",2)
    panels["guestDiskRatio"]=series_table("Guest filesystem used / capacity", "Fraction used of guest-agent capacity. This is not exactly df Use% when reserved blocks exist.",f'({fu}) / ({fc})',fa,"percentunit",2)
    guest_cpu=panels['vcpuUse']['spec']['queries'][0]['spec']['plugin']['spec']['query']
    # Configured vCPUs = cores per socket × sockets × threads per core.
    # CPU has source=domain, while source=guest applies to guest memory.
    guest_cores=" * ".join("("+metric("kubevirt_vm_resource_requests",f',resource="cpu",unit="{dimension}",source="domain"')+")" for dimension in ["cores","sockets","threads"])
    host_cpu=f'(1 - avg by ({hk}) (rate(node_cpu_seconds_total{{{hv},mode="idle"}}[5m]))) and on (cluster_name) ({virtualization_clusters})'
    for key,title,expr,alias in [
        ('guestCpuGauge','Busiest VM CPU',f'({guest_cpu}) / ({guest_cores} > 0)',a),
        ('guestMemoryGauge','Most used VM memory',f'({used}) / ({total} > 0)',a),
        ('guestDiskGauge','Most used VM filesystem',f'({fu}) / ({fc} > 0)',fa),
        ('hostCpuGauge','Busiest Harvester host CPU',host_cpu,'${cluster_name} · ${node}'),
        ('hostMemoryGauge','Most used Harvester host memory',f'1 - (({hostavail}) / ({hosttotal} > 0))','${cluster_name} · ${node}')]:
        panels[key]=utilization_gauge(title,'Highest measured utilization at the selected end, identified by resource. Orange starts at 80%, red at 90%. Host gauges stay cluster-wide; guest gauges follow VM and namespace filters. Missing measurements are not zero.',expr,alias)
    variables=[variable("vm_cluster","Harvester cluster","k8s_cluster_name","kubevirt_vmi_info","Harvester cluster exporting native KubeVirt metrics."),variable("vm_namespace","VM namespace","namespace",'kubevirt_vmi_info{k8s_cluster_name=~"${vm_cluster}"}',"VM namespace, not the namespace of the OTel collector."),variable("vm_name","Virtual machine","name",'kubevirt_vmi_info{k8s_cluster_name=~"${vm_cluster}",namespace=~"${vm_namespace}"}',"Currently observed VMs.")]
    rows=[row(2,'guestCpuGauge','guestMemoryGauge','guestDiskGauge'),row(2,'hostCpuGauge','hostMemoryGauge'),row(3,"guestUsed","guestAvailable","guestTotal"),row(3,"domainRequest","domainLimit","configuredGuest"),row(3,"vcpuUse","vcpuRequest","vcpuLimit"),row(3,"resident","guestMissing"),row(3,"hostUsed","hostAvailable"),row(3,"hostRequests","hostLimits"),row(3,"guestDiskRatio"),row(3,"guestDiskUsed","guestDiskCapacity")]
    return dashboard("Harvester VM & Host Health","Guest OS usage versus VM reservations and host consumption; guest filesystem metrics with explicit data coverage.",panels,rows,variables,True)


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    documents=[("01-application-sre-overview.yaml",application_dashboard()),("02-workload-resource-efficiency.yaml",resource_dashboard()),("03-kubernetes-platform-health.yaml",platform_dashboard()),("04-traefik-ingress-health.yaml",traefik_dashboard()),("05-harvester-vm-host-health.yaml",harvester_dashboard())]
    for filename,document in documents:
        (OUT/filename).write_text(yaml.safe_dump(document,sort_keys=False,allow_unicode=True,width=1000),encoding="utf-8")
        print(f"generated {OUT/filename}")

if __name__=="__main__": main()
