r"""Generates web-traffic.ndjson: the "Web traffic (nginx-proxy)" Kibana
dashboard over the proxy-ssl access logs this project ships.

    python3 gen_dashboard.py web-traffic.ndjson ['<default KQL query>']

Edit this file rather than the .ndjson, then regenerate. Import with:

    curl -u elastic:<ES_PASS> -H kbn-xsrf:true \
      'https://<kibana>/api/saved_objects/_import?overwrite=true' \
      -F file=@web-traffic.ndjson

It includes a data view with the fixed id `filebeat-docker` that all panels
reference.
"""
import json, sys

DV = "filebeat-docker"
ACCESS = 'event.dataset : "nginx.access"'
ASSETS = ("not url.path : (*.js or *.css or *.map or *.png or *.jpg or *.jpeg "
          "or *.gif or *.svg or *.ico or *.webp or *.avif or *.woff or *.woff2 or *.ttf)")

# optional dashboard-wide default query, e.g. to hide admin vhosts on one host
DEFAULT_QUERY = sys.argv[2] if len(sys.argv) > 2 else ""

objects = []


def count(label, kql=None):
    c = {"label": label, "customLabel": True, "dataType": "number", "operationType": "count",
         "sourceField": "___records___", "isBucketed": False, "params": {"emptyAsNull": False}}
    if kql:
        c["filter"] = {"query": kql, "language": "kuery"}
    return c


def unique(label, field):
    return {"label": label, "customLabel": True, "dataType": "number", "operationType": "unique_count",
            "sourceField": field, "isBucketed": False, "params": {"emptyAsNull": False}}


def total(label, field, fmt=None):
    c = {"label": label, "customLabel": True, "dataType": "number", "operationType": "sum",
         "sourceField": field, "isBucketed": False, "params": {"emptyAsNull": False}}
    if fmt:
        c["params"]["format"] = {"id": fmt, "params": {"decimals": 1}}
    return c


def terms(label, field, size, order_by, dtype="string", other=False):
    return {"label": label, "customLabel": True, "dataType": dtype, "operationType": "terms",
            "sourceField": field, "isBucketed": True,
            "params": {"size": size, "orderBy": {"type": "column", "columnId": order_by},
                       "orderDirection": "desc", "otherBucket": other, "missingBucket": False,
                       "parentFormat": {"id": "terms"}}}


def histogram():
    return {"label": "@timestamp", "dataType": "date", "operationType": "date_histogram",
            "sourceField": "@timestamp", "isBucketed": True,
            "params": {"interval": "auto", "includeEmptyRows": True, "dropPartials": False}}


def filters(label, items):
    return {"label": label, "customLabel": True, "dataType": "string", "operationType": "filters",
            "isBucketed": True,
            "params": {"filters": [{"input": {"query": q, "language": "kuery"}, "label": l}
                                   for l, q in items]}}


def lens(oid, title, vis_type, columns, visualization, query=ACCESS):
    """columns: ordered list of (id, column)."""
    objects.append({
        "type": "lens", "id": oid, "managed": False,
        "attributes": {
            "title": title, "description": "", "visualizationType": vis_type,
            "state": {
                "datasourceStates": {"formBased": {"layers": {"layer1": {
                    "columnOrder": [i for i, _ in columns],
                    "columns": dict(columns), "incompleteColumns": {}, "sampling": 1}}}},
                "visualization": visualization,
                "query": {"query": query, "language": "kuery"},
                "filters": [], "internalReferences": [], "adHocDataViews": {},
            },
        },
        "references": [{"type": "index-pattern", "id": DV,
                        "name": "indexpattern-datasource-layer-layer1"}],
    })
    return oid


def metric(oid, title, col, query=ACCESS):
    return lens(oid, title, "lnsMetric", [("m", col)],
                {"layerId": "layer1", "layerType": "data", "metricAccessor": "m"}, query)


def table(oid, title, columns, query=ACCESS):
    return lens(oid, title, "lnsDatatable", columns,
                {"layerId": "layer1", "layerType": "data",
                 "columns": [{"columnId": i, "isTransposed": False} for i, _ in columns]}, query)


def donut(oid, title, field, size=8):
    return lens(oid, title, "lnsPie",
                [("g", terms(title, field, size, "m", other=True)), ("m", count("Requests"))],
                {"shape": "donut", "layers": [{
                    "layerId": "layer1", "layerType": "data", "primaryGroups": ["g"], "metrics": ["m"],
                    "numberDisplay": "percent", "categoryDisplay": "default",
                    "legendDisplay": "default", "nestedLegend": False}]})


def stacked(oid, title, split_col, legend="right"):
    return lens(oid, title, "lnsXY",
                [("x", histogram()), ("s", split_col), ("y", count("Requests"))],
                {"legend": {"isVisible": True, "position": legend},
                 "valueLabels": "hide", "fittingFunction": "None",
                 "preferredSeriesType": "bar_stacked",
                 "axisTitlesVisibilitySettings": {"x": False, "yLeft": False, "yRight": True},
                 "layers": [{"layerId": "layer1", "layerType": "data", "seriesType": "bar_stacked",
                             "xAccessor": "x", "accessors": ["y"], "splitAccessor": "s"}]})


# ---- panels: (lens id, w, h) per row; grid is 48 columns wide
rows = [
    [(metric("web-traffic-requests", "Requests", count("Requests")), 8, 6),
     (metric("web-traffic-visitors", "Unique IPs", unique("Unique IPs", "source.ip")), 8, 6),
     (metric("web-traffic-4xx", "4xx responses",
             count("4xx", "http.response.status_code >= 400 and http.response.status_code < 500")), 8, 6),
     (metric("web-traffic-5xx", "5xx responses", count("5xx", "http.response.status_code >= 500")), 8, 6),
     (metric("web-traffic-bots", "Bot requests", count("Bots", 'user_agent.device.name : "Spider"')), 8, 6),
     (metric("web-traffic-bytes", "Data sent", total("Data sent", "http.response.body.bytes", "bytes")), 8, 6)],
    [(stacked("web-traffic-by-domain", "Requests by domain",
              terms("Domain", "destination.domain", 8, "y", other=True)), 30, 14),
     (stacked("web-traffic-status", "Responses by status class",
              filters("Status", [("2xx", "http.response.status_code < 300"),
                                 ("3xx", "http.response.status_code >= 300 and http.response.status_code < 400"),
                                 ("4xx", "http.response.status_code >= 400 and http.response.status_code < 500"),
                                 ("5xx", "http.response.status_code >= 500")]), "bottom"), 18, 14)],
    [(table("web-traffic-domains", "Domains",
            [("d", terms("Domain", "destination.domain", 20, "r")),
             ("r", count("Requests")), ("u", unique("Unique IPs", "source.ip")),
             ("e", count("Errors (4xx/5xx)", "http.response.status_code >= 400"))]), 18, 14),
     (table("web-traffic-pages", "Top pages (without static assets)",
            [("d", terms("Domain", "destination.domain", 10, "r")),
             ("p", terms("Path", "url.path", 15, "r")),
             ("r", count("Requests")), ("u", unique("Unique IPs", "source.ip"))],
            f"{ACCESS} and {ASSETS} and not user_agent.device.name : \"Spider\""), 30, 14)],
    [(table("web-traffic-countries", "Countries",
            [("c", terms("Country", "source.geo.country_name", 15, "r")),
             ("r", count("Requests")), ("u", unique("Unique IPs", "source.ip"))]), 16, 13),
     (donut("web-traffic-browsers", "Browsers", "user_agent.name"), 16, 13),
     (donut("web-traffic-os", "Operating systems", "user_agent.os.name"), 16, 13)],
    [(table("web-traffic-referrers", "Referrers (incl. internal navigation)",
            [("f", terms("Referrer", "http.request.referrer", 15, "r")), ("r", count("Requests"))],
            f'{ACCESS} and http.request.referrer : * and not http.request.referrer : "-"'), 24, 13),
     (table("web-traffic-clients", "Top clients",
            [("i", terms("IP", "source.ip", 15, "r", dtype="ip")),
             ("o", terms("Network (AS)", "source.as.organization.name", 1, "r")),
             ("c", terms("Country", "source.geo.country_iso_code", 1, "r")),
             ("r", count("Requests")),
             ("e", count("Errors (4xx/5xx)", "http.response.status_code >= 400"))]), 24, 13)],
    [(table("web-traffic-errors", "Top failing requests (4xx/5xx)",
            [("d", terms("Domain", "destination.domain", 10, "r")),
             ("p", terms("Path", "url.path", 15, "r")),
             ("s", terms("Status", "http.response.status_code", 3, "r", dtype="number")),
             ("r", count("Requests")), ("u", unique("Unique IPs", "source.ip"))],
            f"{ACCESS} and http.response.status_code >= 400"), 48, 15)],
]

panels, refs, y = [], [], 0
for row in rows:
    x = 0
    for n, (oid, w, h) in enumerate(row):
        pid = oid.removeprefix("web-traffic-")
        panels.append({"type": "lens", "panelIndex": pid, "gridData": {"x": x, "y": y, "w": w, "h": h, "i": pid},
                       "embeddableConfig": {"enhancements": {}}, "panelRefName": f"panel_{pid}"})
        refs.append({"name": f"{pid}:panel_{pid}", "type": "lens", "id": oid})
        x += w
    y += max(h for _, _, h in row)

objects.insert(0, {
    "type": "index-pattern", "id": DV, "managed": False,
    "attributes": {"title": DV, "name": "Docker logs (filebeat-docker)", "timeFieldName": "@timestamp"},
    "references": [],
})
objects.append({
    "type": "dashboard", "id": "web-traffic", "managed": False,
    "attributes": {
        "title": "Web traffic (nginx-proxy)",
        "description": "HTTP access logs of the proxy-ssl project, shipped by the filebeat project.",
        "timeRestore": True, "timeFrom": "now-7d", "timeTo": "now",
        "refreshInterval": {"pause": True, "value": 60000},
        "optionsJSON": json.dumps({"useMargins": True, "syncColors": True, "syncCursor": True,
                                   "syncTooltips": False, "hidePanelTitles": False}),
        "panelsJSON": json.dumps(panels),
        "kibanaSavedObjectMeta": {"searchSourceJSON": json.dumps({
            "query": {"query": DEFAULT_QUERY, "language": "kuery"},
            "filter": []})},
    },
    "references": refs,
})

# Without these Kibana replays every migration since 7.x on import, and the
# old Lens ones choke on the current state format. Values as of Kibana 9.5.
VERSIONS = {"lens": "10.1.0", "dashboard": "10.3.0", "index-pattern": "8.0.0"}
for o in objects:
    o["coreMigrationVersion"] = "8.8.0"
    o["typeMigrationVersion"] = VERSIONS[o["type"]]

with open(sys.argv[1], "w") as f:
    for o in objects:
        f.write(json.dumps(o, separators=(",", ":")) + "\n")
print(len(objects), "objects")
