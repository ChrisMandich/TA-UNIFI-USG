#! /usr/bin/env python
import requests, json, time, pickle, os

def getConfig(file_name):
    # Import Configuration File
    try:
        with open(file_name) as json_data_file:
            config = json.load(json_data_file)
    except:
        printJSONError("Configuration File (%s) DNE." % file_name)
	printJSONError("Current Working Directory: %s" % os.getcwd())
        printJSONError("Splunk Home Environment Variable: %s" % os.environ['SPLUNK_HOME'])
        quit()
    try:
        config['username'], config['password'], config['base_url'], config['site']
    except:
        printJSONError("Configuration File (%s), is not valid." % file_name)
        quit()
    return config['username'], config['password'], config['base_url'], config['site']

def getLastEventID(file_name):
    # Import Last Event ID
    try:
        last_event_id = pickle.load(open(file_name, "rb"))
    except:
        last_event_id = "0"
        printJSONError("Last Event ID not saved, setting to 0")

    return last_event_id

def setLastEventID(event_id):
    try:
        pickle.dump(event_id, open("save.p", "wb"))
    except:
        printJSONError("Unable to update last_event_id")

def loginUNIFI(base_url, username, password):
    # Setup Long Address
    LOGIN_API = base_url + '/api/login'

    # Setup Authorization Data
    d_Auth = {
        'username': username,
        'password': password,
        'remember': False,
        'strict': True
    }
    
    # Create Session and Login to Controller
    session = requests.session()
    session.get(LOGIN_API,verify=False)

    # Loging to Controller
    j_Auth = json.dumps(d_Auth)
    l_response = session.post(LOGIN_API, data=j_Auth, verify=False)

    return session, l_response

def queryEvents(session, base_url, site):
    EVENT_API = base_url + '/api/s/' + site + '/stat/event'

    # Setup Query Headers
    headers = {
            'Content-Type': 'application/json'
        }

    # Get Events from Controller
    r_response = session.get(EVENT_API, headers=headers, verify=False)

    event_data = r_response.json()['data']

    return event_data, r_response

def getUserDetails(user, session, base_url, site):
    REQUEST_URL = base_url + "/api/s/" + site + "/stat/user/" + user

    # Setup Query Headers
    headers = {
        'Content-Type': 'application/json'
    }
    
    # Get User Details from Controller
    r_response = session.get(REQUEST_URL, headers=headers, verify=False)
    
    # Return Details and Response
    details = r_response.json()['data']
    return details, r_response

def printEvents(event_data, last_event_id,  session, base_url, site):
    # Loop through events
    for event in event_data:
        # Check to see if event is new. 
        if event['_id'] > last_event_id:
            try:
                # Check to see if user is provided
                if 'user' in event:
                    # Converts user to String
                    user = str(event['user'])
                    # Get User Details and Response 
                    details, r_response = getUserDetails(user, session, base_url, site)
                    # Check Status Code and add user_details to JSON
                    if r_response.status_code == 400:
                        details = r_response['meta']['msg']
                        event['user_details'] = details
                    elif r_response.status_code == 200:
                        event['user_details'] = details[0]
                    else:
                        event['user_details'] = "none"
            except:
                # Print user_details_exception if request fails. 
                event['user_details'] = "exception"
            # Print JSON event to OUTPUT
            print json.dumps(event)

def printJSONError(Error_Details):
    error_time = time.strftime("%FT%R:%SZ",time.gmtime())
    error = {
        'datetime': error_time,
        'type': 'error',
        'details': Error_Details
    }
    print json.dumps(error)

def main(): 
    # Set file names for Pickle and Config
    config_file_name = "config.json"
    pickle_file_name = "save.p"
    unifi_dir = os.environ['SPLUNK_HOME'] + "/etc/apps/TA-UNIFI-USG/bin/"
    
    # Change Working Directory
    try:
        os.chdir(unifi_dir)
    except:
        printJSONError("Directory Change Failed: %s" % unifi_dir)
        quit()

    # Get Configuration and Last Event ID
    username, password, base_url, site = getConfig(config_file_name)
    last_event_id = getLastEventID(pickle_file_name)
    
    # Create Session with Controller
    session, l_response = loginUNIFI(base_url, username, password)
    # Check to see if Session Was Successful
    if l_response.status_code == 200:
        event_data, r_response = queryEvents(session, base_url, site)
        # Check to see if Event Request was Successful
        if r_response.status_code == 200:
            printEvents(event_data, last_event_id, session, base_url, site)
            setLastEventID(event_data[0]['_id'])  
        else:
            printJSONError("Event Request Failure, Status Code:%s" % r_response.status_code)
    else:
        printJSONError("Login Failure, Status Code:%s" % l_response.status_code)

main()

