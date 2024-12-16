import dash
from dash import html, dcc, dash_table
from dash.dependencies import Input, Output, State
import plotly.express as px
import pandas as pd
import numpy as np
from typing import Optional, Dict
from code_evolution import CodeEvolutionHandler
import json


class ModifiedCodeEvolutionHandler(CodeEvolutionHandler):
    def process_with_reflection(self, code_requirements: list, max_attempts: int = 20, dummy_mode=False) -> Optional[
        str]:
        return super().process_with_reflection(code_requirements, max_attempts, dummy_mode)


class DataContextManager:
    def __init__(self):
        self.current_data = None
        self.plot_type = None
        self.data_summary = None

    def update_context(self, df: pd.DataFrame, plot_type: str) -> Dict:
        """Update the data context with current state"""
        self.current_data = df
        self.plot_type = plot_type

        # Generate data summary
        self.data_summary = {
            'shape': df.shape,
            'columns': list(df.columns),
            'summary_stats': df.describe().to_dict(),
            'current_visualization': plot_type,
            'data_types': df.dtypes.astype(str).to_dict(),
            'sample_data': df.head(3).to_dict('records')
        }

        return self.data_summary

    def get_context_prompt(self) -> str:
        """Generate a context prompt for the LLM"""
        if not self.data_summary:
            return "No data context available."

        context = f"""
Current Data Context:
- Dataset Shape: {self.data_summary['shape']}
- Columns: {', '.join(self.data_summary['columns'])}
- Current Visualization: {self.plot_type}
- Data Sample: {json.dumps(self.data_summary['sample_data'], indent=2)}
- Column Types: {json.dumps(self.data_summary['data_types'], indent=2)}

You can reference this data structure in your response. Available operations:
1. Data manipulation (filtering, aggregation)
2. Visualization changes (plot type, metrics)
3. Statistical analysis
4. Table updates
"""
        return context


# Initialize the app
app = dash.Dash(__name__)

# Create some dummy data for the graph
np.random.seed(42)
df = pd.DataFrame({
    'x': np.random.normal(0, 1, 300),
    'y': np.random.normal(0, 1, 300),
    'category': np.random.choice(['A', 'B', 'C'], 300)
})

# Initialize handlers
code_handler = ModifiedCodeEvolutionHandler()
context_manager = DataContextManager()

# Layout
app.layout = html.Div([
    # Header
    html.H1("Interactive Dashboard with LLM Integration", className="mb-4"),

    # Left Column - Graph Section
    html.Div([
        html.H3("Data Visualization"),
        dcc.Dropdown(
            id='plot-type',
            options=[
                {'label': 'Scatter Plot', 'value': 'scatter'},
                {'label': 'Box Plot', 'value': 'box'}
            ],
            value='scatter',
            className="mb-4"
        ),
        dcc.Graph(id='main-graph'),

        # Add data context display
        html.Div([
            html.H4("Current Data Context"),
            html.Pre(id='data-context-display',
                     style={'whiteSpace': 'pre-wrap',
                            'wordBreak': 'break-all',
                            'backgroundColor': '#f8f9fa',
                            'padding': '10px'})
        ]),
    ], style={'width': '60%', 'display': 'inline-block', 'padding': '20px'}),

    # Right Column - Chat and Table
    html.Div([
        # Chat Section
        html.H3("LLM Chat Interface"),
        dcc.Input(
            id='chat-input',
            type='text',
            placeholder='Enter your message...',
            style={'width': '100%', 'marginBottom': '10px'}
        ),
        html.Button('Send', id='send-button', n_clicks=0),
        html.Div(id='chat-output',
                 style={'height': '200px', 'overflowY': 'scroll', 'border': '1px solid #ddd', 'padding': '10px',
                        'marginTop': '10px'}),

        # Table Section
        html.H3("Data Table", style={'marginTop': '20px'}),
        dash_table.DataTable(
            id='data-table',
            columns=[{'name': i, 'id': i} for i in df.head().columns],
            data=df.head().to_dict('records'),
            style_table={'overflowX': 'auto'},
            style_cell={'textAlign': 'left'},
            style_header={
                'backgroundColor': 'rgb(230, 230, 230)',
                'fontWeight': 'bold'
            }
        ),
    ], style={'width': '35%', 'float': 'right', 'padding': '20px'}),
], style={'padding': '20px'})


# Callback for updating the graph and context
@app.callback(
    [Output('main-graph', 'figure'),
     Output('data-context-display', 'children')],
    [Input('plot-type', 'value')]
)
def update_graph_and_context(plot_type):
    # Update data context
    context = context_manager.update_context(df, plot_type)

    # Create figure
    if plot_type == 'scatter':
        fig = px.scatter(df, x='x', y='y', color='category',
                         title='Interactive Scatter Plot')
    else:
        fig = px.box(df, x='category', y='y',
                     title='Box Plot by Category')

    return fig, json.dumps(context, indent=2)


# Callback for handling chat interactions
@app.callback(
    Output('chat-output', 'children'),
    [Input('send-button', 'n_clicks')],
    [State('chat-input', 'value'),
     State('chat-output', 'children')]
)
def update_chat(n_clicks, input_value, current_output):
    if not input_value:
        return current_output

    try:
        # Get current data context
        context_prompt = context_manager.get_context_prompt()

        # Combine user input with context
        full_prompt = f"{context_prompt}\n\nUser Query: {input_value}"

        # Process the input using CodeEvolutionHandler
        code_requirements = [full_prompt]
        result = code_handler.process_with_reflection(code_requirements)

        # Create new chat message
        new_message = html.Div([
            html.Strong("You: "), html.Span(input_value),
            html.Br(),
            html.Strong("Assistant: "), html.Span(str(result) if result else "Sorry, I couldn't process that request.")
        ])

        # Append to existing messages
        if current_output is None:
            return [new_message]
        return current_output + [new_message]

    except Exception as e:
        return current_output + [html.Div([
            html.Strong("Error: "),
            html.Span(f"An error occurred: {str(e)}")
        ])]


if __name__ == '__main__':
    app.run_server(debug=True)