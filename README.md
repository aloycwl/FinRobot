# AC finrobot Prediction

Demo
[![Watch on YouTube](https://img.youtube.com/vi/dOocHHLX814/0.jpg)](https://www.youtube.com/watch?v=dOocHHLX814)

AC finrobot Prediction is a mini AI program that allows users to select different free-tier AI models for predicting various financial data, including cryptocurrency and stock prices. This tool uses multiple AI APIs to generate predictions based on the selected model and data type.

Using
- Time series data
- Latest news
- Market depth
- Market sentiment

Data source
- Time series data from OKX
- News from Crypto Panic
- Market depth from OKX
- Market sentiment from Alternate

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
5. **Nvidia** - For access to many free and unlimited models ([Get API Key](https://build.nvidia.com/settings/api-keys))

Set up your environment variables:

```bash
export AV=your_alphavantage_api_key
export CA=your_cloudflare_account_id
export CK=your_cloudflare_api_key
export GK=your_gemini_api_key
export QK=your_groq_api_key
export NV=your_nvidia_api_key
```

## Usage

```bash
python predict.py
```

```python
#predict.py
cf.ml = 'nvidia'
cf.mo = 'qwen/qwen3-235b-a22b'
```

### Parameters:

- `cf.mo`: AI service provider (cloudflare, gemini, groq, nvidia, ollama)
- `cf.ml`: ID of the model
- `prediction_type`: Type of financial prediction from prompt.py

### Examples:

```python
# using nvidia API
cf.ml = 'nvidia'
# qwen model
cf.mo = 'qwen/qwen3-235b-a22b'

# using Google
cf.ml = 'google'
# gemini model
cf.mo = 'gemini-2.5-pro'
```

## Available Models
Go to the respective models documentation or official page to find out more

## Prediction Types (prompt.py)
View prompt.py to find out more

## Key Project Structure

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

## Upcoming Improvements
![AI Trading](https://cdn.jsdelivr.net/gh/aloycwl/FinRobot@main/img/ai_trading.png)