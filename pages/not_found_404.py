import dash
from dash import html

dash.register_page(__name__, path="/404", title="404 Page Not Found", nav=False)

layout = html.Center(html.H1("Error 404 Page Not Found"), className="display-3 my-5")
