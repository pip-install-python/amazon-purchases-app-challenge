import dash
from dash import *
from dash_nivo import ResponsiveCircle
import dash_ag_grid as dag
import polars as pl
import json
import os
from flask_caching import Cache
from flask_executor import Executor
import plotly.express as px
from dash_dynamic_grid_layout import DashGridLayout, DraggableWrapper
import dash_mantine_components as dmc
from dash_iconify import DashIconify
from dash.exceptions import PreventUpdate

# Set the React version
dash._dash_renderer._set_react_version("18.2.0")

# Initialize the Dash app
app = dash.Dash(__name__, suppress_callback_exceptions=True, assets_folder="assets")

# Setup caching and executor
cache = Cache(
    app.server, config={"CACHE_TYPE": "filesystem", "CACHE_DIR": "cache-directory"}
)
executor = Executor(app.server)

# Get list of states
states = [
    f.split("_")[0] for f in os.listdir("assets/states") if f.endswith("_purchases.csv")
]


# Pre-aggregate total values for each state (limited to first 100 entries)
@cache.memoize(timeout=3600)  # Cache for 1 hour
def get_state_totals():
    totals = {}
    for state in states:
        df = pl.read_csv(f"assets/states/{state}_purchases.csv").head(100)
        totals[state] = (df["Purchase Price Per Unit"] * df["Quantity"]).sum()
    return totals


state_totals = get_state_totals()

# Define the layout
app.layout = dmc.MantineProvider(
    [
        html.Div(
            [
                html.Div(
                    children=[
                        html.Center(
                            [
                                html.Img(
                                    src="assets/imgs/amazon_logo.png",
                                    style={"width": "10vw", "height": "7vh", 'backgroundColor': 'white'},
                                )
                            ]
                        ),
                        html.H2(id="total-value", style={"textAlign": "center"}),
                        dmc.Group(
                            [
                                dcc.Dropdown(
                                    id="state-dropdown",
                                    options=[{"label": "All States", "value": "All"}]
                                    + [
                                        {"label": state, "value": state}
                                        for state in states
                                    ],
                                    value="All",
                                    multi=False,
                                    style={
                                        "width": "80vw",
                                    },
                                ),
                                dmc.Menu(
                                    [
                                        dmc.MenuTarget(
                                            dmc.ActionIcon(
                                                DashIconify(
                                                    icon="icon-park:add-web", width=20
                                                ),
                                                size="lg",
                                                color="#fff",
                                                variant="filled",
                                                id="action-icon",
                                                n_clicks=0,
                                                mb=8,
                                                style={"backgroundColor": "#fff"},
                                            )
                                        ),
                                        dmc.MenuDropdown(
                                            [
                                                dmc.MenuItem(
                                                    "Add Dynamic Component",
                                                    id="add-dynamic-component",
                                                    n_clicks=0,
                                                ),
                                                dmc.MenuItem(
                                                    "Edit Dynamic Layout",
                                                    id="edit-mode",
                                                    n_clicks=0,
                                                ),
                                            ]
                                        ),
                                    ],
                                    transitionProps={
                                        "transition": "rotate-right",
                                        "duration": 150,
                                    },
                                    position="right",
                                ),
                            ],
                        ),
                        DashGridLayout(
                            id="grid-layout",
                            items=[
                                DraggableWrapper(
                                    id="circle-packing-wrapper",
                                    children=[
                                        html.H2("Circle Packing Visualization"),
                                        html.Div(
                                            id="circle-packing-container",
                                            style={"height": "600px"},
                                        ),
                                        html.Div(id="zoom-info"),
                                    ],
                                ),
                                DraggableWrapper(
                                    id="tree-map",
                                    children=[
                                        html.H2("Treemap Visualization"),
                                        dcc.Graph(
                                            id="treemap-container",
                                            style={"height": "600px"},
                                        ),
                                    ],
                                ),
                                DraggableWrapper(
                                    id="ag-data-grid",
                                    children=[
                                        html.H2("Data Grid"),
                                        dag.AgGrid(
                                            id="grid",
                                            columnDefs=[
                                                {"field": i}
                                                for i in pl.read_csv(
                                                    f"assets/states/{states[0]}_purchases.csv"
                                                ).columns
                                            ],
                                            defaultColDef={
                                                "resizable": True,
                                                "sortable": True,
                                                "filter": True,
                                            },
                                            columnSize="sizeToFit",
                                            dashGridOptions={
                                                "pagination": True,
                                                "paginationPageSize": 50,
                                            },
                                            className="ag-theme-alpine-dark",
                                        ),
                                    ],
                                ),
                            ],
                            itemLayout=[
                                # wrapper id, x(0-12), y, w(0-12), h(0-12)
                                {
                                    "i": "circle-packing-wrapper",
                                    "x": 0,
                                    "y": 0,
                                    "w": 6,
                                    "h": 4,
                                },
                                {"i": "tree-map", "x": 6, "y": 0, "w": 6, "h": 4},
                                {"i": "ag-data-grid", "x": 0, "y": 4, "w": 12, "h": 4},
                            ],
                            showRemoveButton=False,
                            showResizeHandles=False,
                            rowHeight=150,
                            cols={"lg": 12, "md": 10, "sm": 6, "xs": 4, "xxs": 2},
                            style={"height": "800px"},
                            compactType="horizontal",
                        ),
                        html.Div(id="debug-info"),
                    ]
                ),
                dcc.Store(id="hierarchical-data-store"),
                dcc.Store(id="grid-data-store"),
            ]
        )
    ],
    id="mantine-provider",
    forceColorScheme="dark",
)


@cache.memoize(timeout=3600)
def load_json(file_path):
    with open(file_path, "r") as f:
        data = json.load(f)
    # Limit the children to 100 entries
    if "children" in data:
        data["children"] = data["children"][:100]
    return data


@cache.memoize(timeout=3600)
def load_csv(file_path):
    return pl.read_csv(file_path).head(100).to_dicts()


def load_data_async(selected_state):
    if selected_state == "All":
        hierarchical_data = load_json("assets/hierarchical_purchases.json")
        grid_data = []
        for state in states:
            grid_data.extend(load_csv(f"assets/states/{state}_purchases.csv"))
        total_value = sum(state_totals.values())
    else:
        hierarchical_data = load_json(f"assets/states/{selected_state}_hierarchy.json")
        grid_data = load_csv(f"assets/states/{selected_state}_purchases.csv")
        total_value = state_totals[selected_state]

    total_value_str = f"Total Purchase Value: ${total_value:.2f}"
    return hierarchical_data, grid_data, total_value_str


@app.callback(
    [
        Output("hierarchical-data-store", "data"),
        Output("grid-data-store", "data"),
        Output("total-value", "children"),
    ],
    Input("state-dropdown", "value"),
)
def load_data(selected_state):
    future = executor.submit(load_data_async, selected_state)
    return future.result()


def flatten_hierarchy(node, parent=None):
    flattened = []
    current = {
        "name": node["name"],
        "parent": (
            parent if parent is not None else "All Orders"
        ),  # Use "All Orders" as the top-level parent
        "value": node.get("loc", 0),  # Use 'loc' as value if it exists
    }
    flattened.append(current)
    if "children" in node:
        for child in node["children"]:
            flattened.extend(flatten_hierarchy(child, node["name"]))
    return flattened


@app.callback(
    [
        Output("circle-packing-container", "children"),
        Output("treemap-container", "figure"),
        Output("grid", "rowData"),
        Output("debug-info", "children"),
    ],
    Input("hierarchical-data-store", "data"),
    Input("grid-data-store", "data"),
    State("state-dropdown", "value"),
)
def update_visualizations(hierarchical_data, grid_data, selected_state):
    if not hierarchical_data or not grid_data:
        return dash.no_update, dash.no_update, dash.no_update, "No data available"

    circle_packing = ResponsiveCircle(
        data=hierarchical_data,
        margin={"top": 20, "right": 20, "bottom": 20, "left": 20},
        id="circle-packing",
        colors={"scheme": "nivo"},
        childColor={"from": "color", "modifiers": [["brighter", 0.4]]},
        padding=4,
        enableLabels=True,
        motionConfig="slow",
        labelsSkipRadius=16,
        labelTextColor={"from": "color", "modifiers": [["darker", 2]]},
        borderWidth=1,
        borderColor={"from": "color", "modifiers": [["darker", 0.5]]},
    )

    # Prepare data for treemap
    flattened_data = flatten_hierarchy(hierarchical_data)
    df = pl.DataFrame(flattened_data)

    # Ensure all entries have a parent
    df = df.with_columns(pl.col("parent").fill_null("All Orders"))

    treemap = px.treemap(
        df.to_pandas(),  # Convert to pandas DataFrame
        path=["parent", "name"],
        values="value",
        title=f"Purchase Distribution for {selected_state} (First 100 Entries)",
    )
    treemap.update_traces(textinfo="label+value")
    treemap.update_layout(
        margin=dict(t=50, l=25, r=25, b=25),
        paper_bgcolor="rgba(0,0,0,0)",
        # plot_bgcolor='rgba(0,0,0,0)'
    )

    debug_info = f"Selected State: {selected_state}, Data Points: {len(hierarchical_data['children'])}"

    return circle_packing, treemap, grid_data, debug_info


@app.callback(Output("zoom-info", "children"), Input("circle-packing", "zoomedId"))
def display_zoom_info(zoomedId):
    if zoomedId:
        return f"Zoomed to: {zoomedId}"
    return "No zoom applied"


@callback(
    Output("grid-layout", "showRemoveButton"),
    Output("grid-layout", "showResizeHandles"),
    Input("edit-mode", "n_clicks"),
    State("grid-layout", "showRemoveButton"),
    State("grid-layout", "showResizeHandles"),
    prevent_initial_call=True,
)
def enter_editable_mode(n_clicks, current_remove, current_resize):
    print("Edit mode clicked:", n_clicks)  # Debug print
    if n_clicks is None:
        raise PreventUpdate
    return not current_remove, not current_resize


@callback(
    Output("grid-layout", "items", allow_duplicate=True),
    Input("grid-layout", "itemToRemove"),
    State("grid-layout", "itemLayout"),
    prevent_initial_call=True,
)
def remove_component(key, layout):
    if key:
        items = Patch()
        print(key)
        for i in range(len(layout)):
            if layout[i]["i"] == key:
                del items[i]
                break
        return items
    return no_update


# Run the app
if __name__ == "__main__":
    app.run_server(debug=True, port=8252)
