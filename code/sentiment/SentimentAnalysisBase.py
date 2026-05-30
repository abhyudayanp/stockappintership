import plotly.express as px
import plotly.graph_objects as go


class SentimentAnalysisBase():

    def __init__(self):
        pass

    def set_symbol(self, symbol):
        self.symbol = symbol

    def set_data(self, df):

        self.df = df

    def calc_sentiment_score(self):
        pass

    def get_sentiment_scores(self):
        return self.df

    def calc_sentiment_score(self):
        pass

    def plot_sentiment(self) -> go.Figure:

        column = 'sentiment_score'

        df_plot = self.df.drop(
            self.df[self.df[f'{column}'] == 0].index)

        fig = go.Figure()
        if not df_plot.empty:
            fig.add_trace(go.Bar(
                x=[str(v) for v in df_plot['Date Time']],
                y=[float(v) for v in df_plot[column]],
                marker_color="#636efa",
                name="Sentiment"
            ))
            
        fig.update_layout(
            title=f"{self.symbol} Hourly Sentiment Scores",
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(15,20,40,0.8)",
            font=dict(color="#e2e8f0", family="Inter, sans-serif"),
            margin=dict(l=10, r=10, t=40, b=10),
        )
        return fig
