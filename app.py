from flask import Flask ,render_template,request
from flask.wrappers import Request
from pyasn1.type.univ import Null
import tensorflow as tf
import pickle
from tensorflow.keras.preprocessing.sequence import pad_sequences
from werkzeug.utils import redirect
import pyrebase
import datetime

#firebase things 
config1 = {
    "apiKey": "AIzaSyAFlj5Nv1oIBJNFe7P4fUiP1oW-iXKZwPE",
    "authDomain": "searchtap-8fec3.firebaseapp.com",
    "databaseURL":"searchtap-8fec3.firebaseio.com",
    "projectId": "searchtap-8fec3",
    "storageBucket": "searchtap-8fec3.appspot.com",
    "messagingSenderId": "999873420985",
    "appId": "1:999873420985:web:1b41ad0672a13cfe5dc568",
    "measurementId": "G-EB9GRR80MV"
}

firebase = pyrebase.initialize_app(config1)
auth = firebase.auth()

config2 = {
    "apiKey": "AIzaSyAFlj5Nv1oIBJNFe7P4fUiP1oW-iXKZwPE",
    "authDomain": "searchtap-8fec3.firebaseapp.com",
    "databaseURL":"https://searchtap-8fec3-default-rtdb.firebaseio.com",
    "projectId": "searchtap-8fec3",
    "storageBucket": "searchtap-8fec3.appspot.com",
    "messagingSenderId": "999873420985",
    "appId": "1:999873420985:web:1b41ad0672a13cfe5dc568",
    "measurementId": "G-EB9GRR80MV"
}
firebase2 = pyrebase.initialize_app(config2)
userdb=firebase2.database()

#opening my tokenizer
with open(r'./models/tokenizer.pickle', 'rb') as handle:
    tokenizer = pickle.load(handle)


#loading my gggggenius model
model = tf.keras.models.load_model(r'./models/profanity_model.h5')
max_length = 80
trunc_type = "post"
padding_type = "post"


#initialising my flask app
app = Flask(__name__)

@app.route('/')
def root():
    global username
    username = ""
    return render_template('homepage.html')

@app.route('/homepage')
def index():
    return render_template('homepage.html', username = username)

@app.route('/search',methods = ['POST'])
def checkprofane():
    global username
    sentence = []
    sentence.append(request.form['searchkey']) 
    tokenized = tokenizer.texts_to_sequences(sentence)
    padded = pad_sequences(tokenized,maxlen = max_length,padding = padding_type, truncating = trunc_type)
    res= model.predict(padded)
    asplain = float(*res[0])
    if asplain>0.5:
        return render_template('searchResults.html', data = asplain,sentence = sentence[0],username1 = username)
    else:
        mydict = scrapping(sentence)
        #if user logged in, add to history
        if(username):
            curtime = datetime.datetime.now().strftime('%d-%m-%Y %H:%M:%S')
            data  = {"Search": sentence[0],"Time":curtime}
            userdb.child("history").child(username).child().push(data)
        return render_template('searchResults.html', results = mydict,sentence = sentence[0],username1 = username)


@app.route('/register',methods = ['GET','POST'])
def regpage():
    return render_template('registration.html')

@app.route('/', methods =['POST'])
def register():
    fname = request.form['fname']
    lname = request.form['lname']
    email = request.form['email']
    phno = request.form['number']
    pwd1 = request.form['password1']
    gender = request.form['gender']
    data={"fName":fname,"lName":lname,"Phone no":phno,"Gender":gender,"Email":email}
    #eforchild = email.replace(".",",")
    userdb.child("users").child().push(data)
    try:
        user = auth.create_user_with_email_and_password(email,pwd1)
        auth.get_account_info(user['idToken'])
        return render_template('login.html')
    except:
        message = "Email already registered."
        return render_template('registration.html', message1 = message)
    

@app.route('/login',methods = ['GET'])
def loginpage():
    return render_template('login.html')

@app.route('/login',methods = ["POST"])
def logincheck():
    email = request.form['email']
    password = request.form['password']
    try:
        auth.sign_in_with_email_and_password(email,password)
        #getting username
        res = userdb.child('users').child().order_by_child("Email").equal_to(email).get()
        global username
        username=res.each()[0].val()['fName']
        return render_template('homepage.html', username = username)
    except:
        return render_template('login.html', message1 = "Invalid login credentials." )

@app.route('/',methods = ["GET","POST"])
def signout():
    global username
    return render_template('homepage.html',username = "")

@app.route("/history",methods = ["GET","POST"])
def history():
    global username
    res = userdb.child('history').child(username).get()
    searchkey=[]
    timelist=[]
    if res.each():
        for i in res.each():
            searchkey.append(i.val()["Search"])
            timelist.append(i.val()["Time"])
        res= {}
        for i,j in zip(timelist,searchkey):
            res[i] = j
        return render_template('history.html', results = res, username1 = username)
    else:
        return render_template('history.html',username1 = username)  
          
@app.route("/aboutus",methods = ["GET","POST"])
def aboutus():
    return render_template('aboutus.html')

#for scrapping part
from itertools import zip_longest
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

#declaration guys
Path = r"./scrapping and profanity detector/chromedriver.exe"

heading_text = []
links = []
description = []

def scrapping(sentence):
    driver = webdriver.Chrome(Path) #creating the driver
    #converting the search query into link address
    #keys=list(map(str,input().split()))
    search = "+".join(key for key in sentence)
    driver.get("https://www.bing.com/search?q="+search)    
    _,_,_ = scrape(driver)
    # time.sleep(1)  ### BASED ON INTERNET CONNECTION EDIT THIS
    #driver.find_element_by_xpath("//a[@aria-label='Page 2']").click()
    driver.get("https://www.bing.com/search?q="+search+"&first=11&FORM=PERE")
    heading_text,links,description = scrape(driver)
    driver.quit()
    results  = cleanit(heading_text,links,description)
    return results

def scrape(driver):   
    heading_text = []
    links = []
    description = [] 
    #until all element is loaded/wait for 15 secs, results are extracted
    elements = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.ID, "b_results"))
            )

    #finding the headings elements
    headings = elements.find_elements_by_tag_name('h2')

    #finding the header content as text from element
    for heading in headings:
        #header = article.find_element_by_tag_name('h2')
        heading_text.append(heading.text.lstrip())
    #print(len(heading_text))
    #clearing headings
    for heading in heading_text:
        if('EXPLORE' in heading):
            heading_text.remove(heading)
    #print(len(heading_text))
    link_elements = elements.find_elements_by_xpath('//h2//a') #finding link elements

    for link in link_elements:
        links.append(link.get_attribute('href')) #finding links


    desc_element = elements.find_elements_by_xpath('//p') #description elements
    for desc in desc_element:
        if desc.text:
            description.append(desc.text.lstrip()) #description as text
    return heading_text,links,description

def cleanit(heading_text,links,description):
    #filtering search results
    for head in heading_text:
        if ("Related searches for" in head) or ('EXPLORE FURTHER' in head) or ('Images of' in head) or ('Videos of' in head) or ("See more" in head): #add other elements also
            heading_text.remove(head)
    for link in links:
        if "bing" in link:
            links.remove(link)

    #because link can't be made empty so
    heading_text = heading_text[:len(links)]
    description = description[:len(links)]
    data= {l: (h, d) for l, h, d in zip_longest(links, heading_text, description)}
    return data




if __name__ == "main":
    app.run(debug=True) 