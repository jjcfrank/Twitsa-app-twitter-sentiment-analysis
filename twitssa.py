from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.wait import WebDriverWait
import pandas as pd
from textblob import TextBlob
import matplotlib.pyplot as plt
from wordcloud import WordCloud
import time
from datetime import datetime, date
from time import sleep
import re
import tkinter as tk
from tkinter import DISABLED, NORMAL, END, W, LEFT
import geocoder

### Below the app engine ###

#Main function that calls the application
def main(word, lang, lat, lon, km):
    #Set path of search engine & initiate the driver

    #Sets path for search engine, initiates the driver, caches the Twitter page
    PATH = "/Applications/chromedriver"
    driver = webdriver.Chrome(PATH)
    driver.get("https://twitter.com/explore")
    wait = WebDriverWait(driver,10)
    sleep(10)

    #Searches for Twitter search bar using xpath
    search_input = driver.find_element_by_xpath('//input[@aria-label="Search query"]')

    #User inputs & press return
    search_input.send_keys(word + ' ' + lang + ' ' + 'geocode:' + str(lat) + ',' + str(lon) + ',' + str(km) + 'km')
    search_input.send_keys(Keys.RETURN)
    sleep(10)

    #Clicks on the tab 'latest'
    driver.find_element_by_link_text('Latest').click()

    #Collects all tweets in page
    data = []
    tweet_ids = set()
    last_position = driver.execute_script("return window.pageYOffset;")
    scrolling = True

    def get_tweet_data(card):
        #Extracts tweet from the element
        username = card.find_element_by_xpath('.//span').text
        
        #Checks if there is any or more cards & postdate
        try:
            handle = card.find_element_by_xpath('.//span[contains(text(), "@")]').text
        except NoSuchElementException:
            return
        
        try:
            postdate = card.find_element_by_xpath('.//time').get_attribute('datetime')
        except NoSuchElementException:
            return
        
        #HTML locations
        msg = card.find_element_by_xpath('.//div[2]/div[2]/div[1]').text
        replying = card.find_element_by_xpath('.//div[2]/div[2]/div[2]').text
        text = msg + ' ' + replying
        reply_num = card.find_element_by_xpath('.//div[@data-testid="reply"]').text
        retweet_num = card.find_element_by_xpath('.//div[@data-testid="retweet"]').text
        like_num = card.find_element_by_xpath('.//div[@data-testid="like"]').text
        
        #Get emojis
        tgEmo = card.find_elements_by_xpath('.//img[contains(@src, "emoji")]')
        lstEmo = []
        for tag in tgEmo:
            filer = tag.get_attribute('src')
            try:
                emoji = chr(int(re.search(r'svg\/([a-z0-9]+)\.svg', filer).group(1), base=16))
            except AttributeError:
                continue
            if emoji:
                lstEmo.append(emoji)
        emojis = ' '.join(lstEmo)
        
        tweet = (username, handle, postdate, text, emojis, reply_num, retweet_num, like_num)
        return tweet

    #Scroller
    while scrolling:
        page_cards = driver.find_elements_by_xpath('//div[@data-testid="tweet"]')
        for card in page_cards[-15:]:
            tweet = get_tweet_data(card)
            if tweet:
                tweet_id = ''.join(tweet)
                if tweet_id not in tweet_ids:
                    tweet_ids.add(tweet_id)
                    data.append(tweet)
            
        scroll_attempt = 0
        while True:
            # check scroll position
            driver.execute_script('window.scrollTo(0, document.body.scrollHeight);')
            sleep(2)
            curr_position = driver.execute_script("return window.pageYOffset;")
            if last_position == curr_position:
                scroll_attempt += 1
                
                # end of scroll region
                if scroll_attempt >= 3:
                    scrolling = False
                    break
                else:
                    sleep(2) # attempt another scroll
            else:
                last_position = curr_position
                break
    
    # close the web driver
    driver.close()

    #Tidies raw tweet data
    def cleanTweets1():
        tweetList = []
        for i in data:
            tweetList.append(i)
        df = pd.DataFrame(tweetList)
        df = df.rename(columns={df.columns[0]: 'username', df.columns[1]: 'handle', df.columns[2]: 'date', df.columns[3]: 'message', df.columns[4]: 'emojis', df.columns[5]: 'reply_cnt', df.columns[6]: 'retweet_cnt', df.columns[7]: 'like_cnt'})
        return df

    df = cleanTweets1()

    #Prepares tweets for sentiment analysis
    def cleanTweets2(text):
        text = re.sub(r'#', ' ', text)
        text = re.sub(r'\n', ' ', text)
        text = re.sub('(?:\s)@[^, ]*', '', text)

        text = re.sub(r'@[A-Za-z0-9]+', '', text)
        text = re.sub(r'Replying to[\s]+', '', text)
        return text
    
    df['message'] = df['message'].apply(cleanTweets2)

    #Get subjectivity & polarity using TextBlob library
    def getSubjectivity(text):
        return TextBlob(text).sentiment.subjectivity

    def getPolarity(text):
        return TextBlob(text).sentiment.polarity

    #Subjectivity and polarity functions implemented
    df['subjectivity'] = df['message'].apply(getSubjectivity)
    df['polarity'] = df['message'].apply(getPolarity)

    #Get results and store them in the df column as 'positive', 'neutral', 'negative'
    def getAnalysis(score):
        if score < 0:
            return 'negative'
        elif score == 0:
            return 'neutral'
        else:
            return 'positive'

    df['analysis'] = df['polarity'].apply(getAnalysis)

    #Get results and store them in the df column as 'positive', 'neutral', 'negative'
    def getAnalysis(score):
        if score < 0:
            return 'negative'
        elif score == 0:
            return 'neutral'
        else:
            return 'positive'

    df['analysis'] = df['polarity'].apply(getAnalysis)

    #The analysed word
    df['word'] = word

    #Visual representation #1: strength of words scrapped using WordCloud library
    def getWordCloud():
        everyWord = ' '.join([tweets for tweets in df['message']])
        wordCloud = WordCloud(width= 500, height = 300, random_state = 21, max_font_size = 110).generate(everyWord)

        sentWordCloud = plt.figure(figsize=(8,6))
        plt.imshow(wordCloud, interpolation = 'bilinear')
        plt.axis('off')
        sentWordCloud.savefig('sentiment-wordcloud.pdf')

    getWordCloud()

    #Visual representation #2: observe subjectivity and polarity in a scatter plot
    def getSentPolFig():
        sentPolFig = plt.figure(figsize=(8,6))
        for i in range(0, df.shape[0]):
            plt.scatter(df['polarity'][i], df['subjectivity'][i], color='Blue')

        plt.title('Sentiment Analysis')
        plt.xlabel('Polarity')
        plt.ylabel('Subjectivity')
        sentPolFig.savefig('sentiment-polarity.pdf')

    getSentPolFig()

    #Visual representation #3: bar plot of positive, negative and neutral tweets
    def getSentPercFig():
        sentPerc = plt.figure(figsize=(8,6))

        plt.title('Sentiment Analysis')
        plt.xlabel('Sentiment')
        plt.ylabel('Counts')
        df.analysis.value_counts().plot(kind='bar')
        sentPerc.savefig('sentiment-percentage.pdf')

    getSentPercFig()

    #Exports the df to CSV
    def getCsv():
        now = datetime.now()
        timeNow = now.strftime("%d-%m-%Y %H:%M:%S")
        df.to_csv('twitter-sentiment-analysis' + ' - ' + timeNow + '.csv')

    getCsv()

    #Making descriptive stats of positive, negative and neutral tweets
    postweets = df[df.analysis == 'positive']
    postweets = postweets['message']
    neutweets = df[df.analysis == 'neutral']
    neutweets = neutweets['message']
    negtweets = df[df.analysis == 'negative']
    negtweets = negtweets['message']
    postwtperc = str(round((postweets.shape[0] / df.shape[0]) *100, 1)) + "% of people made positive comments about " + word
    neutwtperc = str(round((neutweets.shape[0] / df.shape[0]) *100, 1)) + "% of people made neutral comments about " + word
    negtwtperc = str(round((negtweets.shape[0] / df.shape[0]) *100, 1)) + "% of people made negative comments about " + word

    #Amount of tweets collected
    numberOfTweets = "Tweets extracted: " + str(len(df))

    return [numberOfTweets, postwtperc, neutwtperc, negtwtperc]

### Below the Tkinter code ###

#Placeholder #1: focus out
def focus_out_value_box(widget, widget_text):
    if widget['fg'] == 'Black' and len(widget.get()) == 0:
        widget.delete(0, END)
        widget['fg'] = 'Grey'
        widget.insert(0, widget_text)

#Placeholder #1: focus in
def focus_in_value_box(widget):
    if widget['fg'] == 'Grey':
        widget['fg'] = 'Black'
        widget.delete(0, END)

#Obtains location using Geocoder
def getLocation():
    focus_in_value_box(latlonEntry)
    g = geocoder.ip('me')
    latlon = g.latlng
    lat = latlon[0]
    lon = latlon[1]
    latlonStr = str(lat) + ', ' + str(lon)
    latlonEntry.insert(0, latlonStr)

#Main Tkinter function - activates the main()
def clickGo():
    global wordEntry, kmEntry, latlonEntry
    processing = tk.Label(root, text="Processing...")
    processing.grid(row=7, columns=3, pady=(0, 25))
    processing.config(font=("Georgia", 20, 'italic'))
    root.update()

    #Lat & lon are made float numbers again for main()
    def tidyLocation():
        entry = latlonEntry.get()
        entry = entry.replace(' ', '')
        entry = entry.split(',')
        lat = float(entry[0])
        lon = float(entry[1])
        return lat, lon

    #Activator
    results = main(wordEntry.get(), "lang:en", tidyLocation()[0], tidyLocation()[1], float(kmEntry.get()))

    #Destroys the 'Processing...' label
    processing.destroy()

    #Results box #1: header
    resultsBanner = tk.Label(root, text="#### Results: ####")
    resultsBanner.grid(row=8, columns=3, pady=(0, 20))
    resultsBanner.config(font=("Georgia", 20, "bold"))

    #Results box #2: amount of tweets collected
    results1 = tk.Label(root, text=results[0])
    results1.grid(row=9, columns=3, pady=(0, 7))
    results1.config(font=("Georgia", 15))

    #Results box #3: positive results
    results2 = tk.Label(root, text=results[1])
    results2.grid(row=10, columns=3, pady=(0, 7))
    results2.config(font=("Georgia", 15))

    #Results box #4: neutral results
    results3 = tk.Label(root, text=results[2])
    results3.grid(row=11, columns=3, pady=(0, 7))
    results3.config(font=("Georgia", 15))

    #Results box #5: negative results 
    results4 = tk.Label(root, text=results[3])
    results4.grid(row=12, columns=3, pady=(0, 15))
    results4.config(font=("Georgia", 15))

    #Results box #7: important note of created files
    note = tk.Label(root, text="**Additional two graphs and a CSV file \n have been created in the root folder.")
    note.grid(row=13, columns=3, pady=(0, 7))    
    note.config(font=("Georgia", 15, "italic"))  

#Creates frame & title
root = tk.Tk()
root.title("Twitssa")

#Twitssa Logo
logoLabel = tk.Label(root, text="Twitssa")
logoLabel.grid(row=0, column=1, pady=(0, 20))
logoLabel.config(font=("Georgia", 44))

#Intro label
introLabel = tk.Label(root, text="Twitssa is a Twitter Scrapper Sentiment Analysis app \n that searches a given word on Twitter and gives an \n in depth sentiment analysis.")
introLabel.grid(row=1, column=1,  pady=(0, 10))
introLabel.config(font=("Georgia", 15))

#Options label
optionsLabel = tk.Label(root, text="Please note:\n * For better results only enter one word \n * Use coordinates in decimal degrees \n * Distance is measured in km radius")
optionsLabel.grid(row=2, column=1,  pady=(0, 30))
optionsLabel.config(font=("Georgia", 15))

#Word label & entry
wordLabel = tk.Label(root, text="Word:")
wordLabel.grid(row=3, column=0)
wordLabel.config(font=("Georgia", 13, "bold"))
wordEntryText = 'Latinx'
wordEntry = tk.Entry(font=("Proxima Nova", 12, "italic"), fg='Grey')
wordEntry.insert(0, wordEntryText)
wordEntry.bind("<FocusIn>", lambda args: focus_in_value_box(wordEntry))
wordEntry.bind("<FocusOut>", lambda args: focus_out_value_box(wordEntry, wordEntryText))
wordEntry.grid(row=3, column=1)

#Latlon label & entry
latlonLabel = tk.Label(root, text="Location (lat & lon):")
latlonLabel.grid(row=4, column=0)
latlonLabel.config(font=("Georgia", 13, "bold"))
latlonEntryText = '54.597271, -5.930110'
latlonEntry = tk.Entry(font=("Proxima Nova", 12, "italic"), fg='Grey')
latlonEntry.insert(0, latlonEntryText)
latlonEntry.bind("<FocusIn>", lambda args: focus_in_value_box(latlonEntry))
latlonEntry.bind("<FocusOut>", lambda args: focus_out_value_box(latlonEntry, latlonEntryText))
latlonEntry.grid(row=4, column=1)

#Button 'get your location'
buttonGeo = tk.Button(root, text="Get your location", command=getLocation)
buttonGeo.grid(row=4, column=2)
buttonGeo.config(font=("Georgia", 13, "bold"))

#Distance label & entry
kmLabel = tk.Label(root, text="Distance (km):")
kmLabel.grid(row=5, column=0)
kmLabel.config(font=("Georgia", 13, "bold"))
kmLabelText = '20'
kmEntry = tk.Entry(font=("Proxima Nova", 12, "italic"), fg='Grey')
kmEntry.insert(0, kmLabelText)
kmEntry.bind("<FocusIn>", lambda args: focus_in_value_box(kmEntry))
kmEntry.bind("<FocusOut>", lambda args: focus_out_value_box(kmEntry, kmLabelText))
kmEntry.grid(row=5, column=1)

#Button 'Go'
buttonGo = tk.Button(root, text="Go", command=clickGo, width=8)
buttonGo.grid(row=6, column=1, pady=(25, 25))
buttonGo.config(font=("Georgia", 20, "bold"))

#Copyright label
cr = tk.Label(root, text="App created by Frank Jimenez | " + str(datetime.now().year))
cr.grid(row=14, column=1, pady=(30, 0))
cr.config(font=("Georgia", 11, "bold"))

#Main loop
root.mainloop()