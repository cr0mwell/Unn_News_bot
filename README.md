UnnParserBot

Version 0.1.0

Telegram bot to parse the https://unn.com.ua website for news.
Allows to specify the article columns to scrap as well as to set the date limits and the batch size.
Columns classification is achieved using pre-trained LogisticRegression ML model.
As a bonus feature the bot allows to classify provided text/news.

Installation & usage

* Create your own Telegram bot: https://core.telegram.org/bots#3-how-do-i-create-a-bot
* Clone the project
* Download the selenium webdriver for Mozilla Firefox: https://github.com/mozilla/geckodriver/releases
  and add its location to the PATH
* Update FIREFOX_PATH and PROJ_PATH variables in $PROJECT_PATH/src/settings.py
  with the respective locations of the Mozilla Firefox executive binary and your project root directory location
* create $PROJECT_PATH/src/bot_token file and add your BOT_TOKEN into it.
* Collect the news from the https://unn.com.ua by running $PROJECT_PATH/src/spider.py.
  NOTE: it may take a few days for the script to collect the full news archive (for 6 months).
  You can set the 'max_page' argument in the get_news() call to set the page limit.
  Obviously this will reduce the accuracy of the ML model that will be trained on this data later.
* Start the bot by running the $PROJECT_PATH/bot.py
  On the first start it will generate ML model and vectorizer objects hence it will take more time
  than usual. Next time on startup the script will load those objects from the files saved in $PROJECT_PATH/src directory
* Enjoy!

Classification ML model

31000 articles were scraped from the https://unn.com.ua website for the train/test dataset.
2 TF-IDF vectorizers (with 'word' and 'char' analyzers) were created to collect 25000 features from the article texts.
Two models where tested on the data collected from the website: LightGBM and LogisticRegression.
LogisticRegression model showed 3-5% better prediction results so it was chosen for a future predictions.
To compare the models accuracy as well as the EDA process please refer to the notebook files:
https://github.com/cr0mwell/Unn_News_bot/tree/master/model_notebooks  