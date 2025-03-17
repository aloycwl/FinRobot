# AC finrobot Prediction

AC finrobot Prediction is a mini AI program that allows users to select different free-tier AI models for predicting various financial data, including cryptocurrency and stock prices. This tool uses multiple AI APIs to generate predictions based on the selected model and data type.

## Features

- Select and interact with various free-tier AI models such as Cloudflare, Gemini, and Groq for different types of predictions.
- Predict cryptocurrency data, forex, and more using different prompts and models.
- Simple command-line interface to select and call prediction functions.
- Fetch time series data from source and store it locally, if free usage is up, fetch from local storage instead.

## API Keys Setup

Before using AC FinRobot, you'll need to obtain API keys from the following services:

1. **AlphaVantage** - For financial data ([Get API Key](https://www.alphavantage.co/support/#api-key))
2. **Cloudflare Workers AI** - For AI model access ([Get API Key](https://developers.cloudflare.com/workers-ai/get-started/))
3. **Google Gemini** - For alternative AI model access ([Get API Key](https://ai.google.dev/docs/gemini-api/setup))
4. **Groq** - For high-speed inference ([Get API Key](https://console.groq.com/keys))

Set up your environment variables:

```bash
export AV=your_alphavantage_api_key
export CA=your_cloudflare_account_id
export CK=your_cloudflare_api_key
export GK=your_gemini_api_key
export QK=your_groq_api_key
```

## Usage

```bash
python predict.py <provider> <model_id> <prediction_type>
```

### Parameters:

- `provider`: AI service provider (cloudflare, gemini, groq)
- `model_id`: ID of the model from models.py
- `prediction_type`: Type of financial prediction from prompt.py

### Examples:

```bash
### Alpha Vantage as the data source

# Cryptocurrency prediction using Cloudflare's Qwen 1.5 7B model
python predict.py cloudflare 27 2

# Stock market analysis using Google Gemini 1.5 pro model
python predict.py gemini 4 3

# Forex trend prediction using Groq's Mixtral model
python predict.py groq 15 1

### yFinance as the data source

# Cryptocurrency prediction using Cloudflare's Qwen 1.5 7B model
python predict.py cloudflare 27 'BTC-USD'

# Stock market analysis using Google Gemini 1.5 pro model
python predict.py gemini 4 'TSLA'

# Forex trend prediction using Groq's Mixtral model
python predict.py groq 15 'EURUSD=X'
```

## Available Models (models.py)
View models.py to find out more

## Prediction Types (prompt.py)
View prompt.py to find out more

## Project Structure

```
ac-finrobot-prediction/
├── prediction.py      # Main script
├── models.py          # AI model definitions
├── prompt.py          # Prediction type templates
└── README.md          # This file
```

## Limitations

- Uses free-tier API services, which have rate limits
- Prediction accuracy depends on model quality and data freshness
- Not recommended for production financial decision-making

## License

MIT

## Disclaimer

This tool is for educational and research purposes only. Financial predictions should not be taken as financial advice. Always consult with a qualified financial advisor before making investment decisions.