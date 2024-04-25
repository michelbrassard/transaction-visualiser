from dash import Dash, dcc, html, Input, Output, State, callback
import plotly.express as px
import base64
import io
from parse import parseDocument
from prepare import get_pivot, get_grouped
import pandas as pd
import numpy as np

uploaded_files = {}
dropdown_options = []

# very important for callbacks
# if not updated click for details won't work when a page is switched using a dropdown
chosen_file = ''
grouped_transactions = pd.DataFrame()


app = Dash(__name__, title='Personal Finance Analytics', suppress_callback_exceptions=True)

app.layout = html.Div(
    className='wrapper',
    children=[
    
    html.Div(
        className='choose-pdf',
        children=[
            html.Div(
                children=[
                    dcc.Dropdown(
                        id='dropdown',
                        value='Select a file'
                    )
            ]),
            dcc.Upload(
                className='drag-drop',
                id='upload-data',
                children=html.A('Upload Files'),
                style={
                    'width': '100%',
                    'lineHeight': '60px',
                    'borderWidth': '1px',
                    'borderStyle': 'dashed',
                    'borderRadius': '1rem',
                    'textAlign': 'center',
                },
                multiple=True
            )
        ]
    ),
    html.Div(
        className='graphs', 
        children=[
            html.Div(id='output-data-upload'),
            html.Div(
                className='details',
                children=[
                    html.H2(id='chart-title', children='Empty data'),
                    html.Div(
                        id='chart-output'
                    )
                ]
            )
    ])
])

@callback(Output('output-data-upload', 'children'),
          Output('dropdown', 'options'),
          Input('upload-data', 'contents'),
          State('upload-data', 'filename'),
          State('upload-data', 'last_modified'))
def update_output(list_of_contents, list_of_names, list_of_dates):
    if list_of_contents is not None:
        for c, n, d in zip(list_of_contents, list_of_names, list_of_dates):
            children = parse_contents(c, n, d) 
        
        return (children, [{'label': get_date_from_filename(filename), 'value': filename} for filename in dropdown_options])
    
    #first output is the calendar, the second is the list of options
    return [html.H1("Upload a file")], ["Select an option"]

def parse_contents(contents, filename, date):
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    try:
        if 'pdf' in filename:
            df = parseDocument(io.BytesIO(decoded), filename)
            
            if filename not in dropdown_options:
                dropdown_options.append(filename)
            
            #date = get_date_from_filename(filename)
            try: 
                pivot = get_pivot(df)
            except Exception:
                return html.Div(
                className='error-message',
                children=[f'No transactions found for: {filename}'])
            
            uploaded_files[filename] = df
            
            global grouped_transactions
            grouped_transactions = get_grouped(df)
            
            global chosen_file
            chosen_file = filename
            
            fig = px.imshow(pivot, 
                            x=['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'], 
                            color_continuous_scale='Reds', 
                            text_auto=True)
            fig.update_xaxes(side="top")
        else :
            return html.Div(
                className='error-message',
                children=['Please provide a PBZ PDF'])
    except Exception:
        return html.Div(
            className='error-message',
            children=['Unable to process file: ' + filename])

    return html.Div([
            html.H1('Transactions for ' + get_date_from_filename(filename)),
            html.Div('File: ' + filename),
            dcc.Graph(
                id='calendar-heatmap',
                figure = fig
            )
        ])

# to get the date nicely from the filename
def get_date_from_filename(filename):
    months = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]
    
    if not filename:
        # this is here because the method is used in the dropdown, and I wanted it to return
        # the 'Select an option' label
        return "Select an option"
    
    parts = filename.split('_')
    date = parts[1]
    year = int(date[:4])
    month_number = int(date[4:6]) - 1 # 'izvod' documents reference the past month
    month_number = month_number - 1 # adjust for position in months list
    
    # This is when a user receives a pdf on January which are transactions from December last year
    if month_number == -1:
        month_number = 11 # december
        year = year - 1
    
    return months[month_number] + ' ' + str(year)

# Define callback to handle click events on the heatmap
@callback(
    Output('chart-title', 'children'),
    Output('chart-output', 'children'),
    [Input('calendar-heatmap', 'clickData')]
)
def display_click_data(click_data):
    if click_data is not None:
        x = click_data['points'][0]['x']
        y = click_data['points'][0]['y']
        
        try:
            date = get_date(x, y, grouped_transactions)
        except Exception:
            #it returns a tuple so that is why the secound output is empty
            #otherwise it returns the pie chart
            return 'No transactions that day', []

        try:
            global chosen_file
            current_dataframe = uploaded_files[chosen_file]
            current_dataframe['date'] = pd.to_datetime(current_dataframe['date'])
            filtered = current_dataframe[current_dataframe['date'] == date]
            pie_chart_fig = px.pie(
                filtered, 
                values='amount', 
                names='location',
                color_discrete_sequence=px.colors.sequential.RdBu
            )
            pie_chart_fig.update_traces(
                textinfo='value',
            )
            pie_chart_fig.update_layout(
                legend=dict(orientation="h",
                            yanchor="bottom", 
                            y=1.02, 
                            xanchor="right", 
                            x=1)
            )
        except Exception:
            return 'Problem with getting data'
        
        if date is not None:
            #string_date = np.datetime_as_string(date, unit='D')
            python_datetime = date.astype('datetime64[s]').astype('O')
            string_date = python_datetime.strftime('%d %B %Y')
            return string_date, dcc.Graph(id='pie-chart',figure = pie_chart_fig)
    
    else:
        #it returns a tuple so that is why the secound output is empty
        #otherwise it returns the pie chart
        return 'Click on a tile to display data', []

# returns the date value from the grouped dataframe using the day name and the week number 
# (coordinates used in the heatmap, for the pivot table)
def get_date(day_name, week, grouped_by_date_dataFrame):
    return grouped_by_date_dataFrame[(grouped_by_date_dataFrame['day_name'] == day_name) & (grouped_by_date_dataFrame['Week'] == week)]['date'].values[0]

@callback(
    Output('output-data-upload', 'children', allow_duplicate=True),
    [Input('dropdown', 'value')],
    prevent_initial_call='initial_duplicate'
)
def update_graph(selected_option):
    if selected_option in uploaded_files and selected_option != 'Select an option':
        global chosen_file
        chosen_file = selected_option
        selected_dataframe = uploaded_files[selected_option]
        
        global grouped_transactions
        grouped_transactions = get_grouped(selected_dataframe)
        
        pivot = get_pivot(selected_dataframe)
        # checks have been made before
        fig = px.imshow(pivot, 
                        x=['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'], 
                        color_continuous_scale='Reds', 
                        text_auto=True)
        fig.update_xaxes(side="top")
        
    else:
        return html.H1('Upload a file')
    
    return html.Div([
            html.H1('Transactions for ' + get_date_from_filename(selected_option)),
            html.Div('File: ' + selected_option),
            dcc.Graph(
                id='calendar-heatmap',
                figure = fig
            )
        ])
    

if __name__ == '__main__':
    app.run(debug=True)
    


