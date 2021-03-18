import os
import json
import requests
import redis
from flask import Flask, request

from quiz.quiz_wmt13 import get_quiz

ACCESS_TOKEN = os.getenv('FB_PAGE_TOKEN')
VERIFY_TOKEN = os.getenv('FB_VERIFY_TOKEN')

# make app
app = Flask(__name__)
app.debug = True
app.secret_key = os.getenv('APP_SECRET')
# make redis
r = redis.StrictRedis(host='localhost', port=6379, db=0, decode_responses=True)
REDIS_EXPIRE_SECONDS = 10800
REDIS_CHUNK_SIZE = 50


# receive messages that Facebook sends our bot
@app.route('/webhook', methods=['GET'])
def init_messenger():
    if request.method == 'GET':
        # Before allowing people to message your bot Facebook has implemented a verify token
        # that confirms all requests that your bot receives came from Facebook.
        token_sent = request.args.get("hub.verify_token")
        # Set get started button and greeting text
        set_get_started_button()
        return verify_fb_token(token_sent)


# sending a message back to user
@app.route('/webhook', methods=['POST'])
def message_back():
    # get whatever message a user sent the bot
    output = request.get_json()
    for event in output['entry']:
        messaging = event['messaging']
        for message in messaging:
            app.logger.debug(message)
            # Facebook Messenger ID for user so we know where to send response back to
            recipient_id = message['sender']['id']
            if not r.exists(recipient_id+':mode'):
                r.set(recipient_id+':mode', 'general', REDIS_EXPIRE_SECONDS)
            if message.get("postback"):  # user clicked/tapped "postback" button in earlier message
                process_postback(recipient_id, message)
            if message.get('message'):
                if message['message'].get("quick_reply"):
                    process_quick_reply(recipient_id, message)
                elif message['message'].get('text'):
                    if r.get(recipient_id+':mode') == 'quiz':
                        process_quiz(recipient_id, message)
                    else:
                        process_text(recipient_id, message)
                # if user send us a GIF, photo, video or any other non-text item
                if message['message'].get('attachments'):
                    pass
    return "Message Processed"


def verify_fb_token(token_sent):
    # take token sent by Facebook and verify it matches the verify token you sent
    # if they match, allow the request, else return an error
    if token_sent == VERIFY_TOKEN:
        return request.args.get("hub.challenge")
    return 'Invalid verification token'


def set_get_started_button():
    get_started_button = {
        "get_started": {
            "payload": "get_started_payload"
        }
    }
    # send an HTTP request back to FB
    fb_response = requests.post('https://graph.facebook.com/v2.6/me/messenger_profile',
                                params={"access_token": ACCESS_TOKEN},
                                data=json.dumps(get_started_button),
                                headers={'content-type': 'application/json'})

    if not fb_response.ok:
        app.logger.debug('Init get_started error. %s: %s' % (fb_response.status_code, fb_response.text))
    else:
        app.logger.debug('Init: added get started button.')


def set_greeting_button():
    greeting = {
        "greeting": [
            {
                "locale": "default",
                "text": "Learn German fast 'n' fun!"
            }
        ]
    }
    # send an HTTP request back to FB
    fb_response = requests.post('https://graph.facebook.com/v2.6/me/messenger_profile',
                                params={"access_token": ACCESS_TOKEN},
                                data=json.dumps(greeting),
                                headers={'content-type': 'application/json'})

    if not fb_response.ok:
        app.logger.debug('Init greeting error. %s: %s' % (fb_response.status_code, fb_response.text))
    else:
        app.logger.debug('Init: added greeting text.')


def process_text(recipient_id, message):
    app.logger.debug('Processing text...')
    pass


def process_quiz(recipient_id, message):
    app.logger.debug('Processing quiz...')
    text = message['message']['text']
    if "Input:" in text:
        start_new_quiz(recipient_id, text)
    else:
        check_answer(recipient_id, text)
    return "success"


def start_new_quiz(recipient_id, text):
    app.logger.debug('Starting new quiz...')
    quiz = get_quiz(text)

    # Post a starting prompt
    prepared_quiz = {
        "messaging_type": "RESPONSE",
        "recipient": {
            "id": recipient_id
        },
        "message": {
            "text": 'Quiz is ready! {} words. {} questions. Let\'s start.'.format(
                quiz['word_count'],
                quiz['question_count']
            )
        }
    }
    # send an HTTP request back to FB
    fb_response = requests.post('https://graph.facebook.com/v10.0/me/messages',
                                params={"access_token": ACCESS_TOKEN},
                                data=json.dumps(prepared_quiz),
                                headers={'content-type': 'application/json'})

    if not fb_response.ok:
        app.logger.debug('Display prepared quiz prompt error. %s: %s' % (fb_response.status_code, fb_response.text))

    # save user quiz in redis
    save_quiz_to_redis(recipient_id, quiz)

    post_question(recipient_id)
    return "success"


def save_quiz_to_redis(recipient_id, quiz):
    r.set(recipient_id + ":current", '0', REDIS_EXPIRE_SECONDS)
    r.set(recipient_id + ":correct", '0', REDIS_EXPIRE_SECONDS)
    r.set(recipient_id + ":total", str(quiz["question_count"]), REDIS_EXPIRE_SECONDS)

    content = quiz["quiz"]
    with r.pipeline() as pipe:
        for q in content:
            pipe.rpush(recipient_id + ":questions_de", q['question_de'], REDIS_EXPIRE_SECONDS)
            pipe.rpush(recipient_id + ":questions_en", q['question_en'], REDIS_EXPIRE_SECONDS)
            pipe.rpush(recipient_id + ":answers", q['answer'], REDIS_EXPIRE_SECONDS)
        pipe.execute()


def clear_quiz_in_redis(recipient_id):
    cursor = '0'
    namespace_pattern = recipient_id + '*'
    while cursor != 0:
        cursor, keys = r.scan(cursor=cursor, match=namespace_pattern, count=REDIS_CHUNK_SIZE)
        if keys:
            r.delete(*keys)
    r.set(recipient_id + ':mode', 'general', REDIS_EXPIRE_SECONDS)
    return True


def post_question(recipient_id):
    # Increment current
    r.incr(recipient_id + ":current")

    # Post a question counter
    current = r.get(recipient_id + ":current")
    total = r.get(recipient_id + ":total")
    app.logger.debug("Posting question {} ....".format(current))

    counter = {
        "messaging_type": "UPDATE",
        "recipient": {
            "id": recipient_id
        },
        "message": {
            "text": "Question {}/{}".format(current, total)
        }
    }
    # send an HTTP request back to FB
    fb_response = requests.post('https://graph.facebook.com/v10.0/me/messages',
                                params={"access_token": ACCESS_TOKEN},
                                data=json.dumps(counter),
                                headers={'content-type': 'application/json'})

    if not fb_response.ok:
        app.logger.debug('Display question counter error. %s: %s' % (fb_response.status_code, fb_response.text))

    # Post a question
    text = r.lpop(recipient_id + ":questions_en")
    r.lpop(recipient_id + ":questions_en") # to remove REDIS_EXPIRE_SECONDS
    question_en = {
        "messaging_type": "UPDATE",
        "recipient": {
            "id": recipient_id
        },
        "message": {
            "text": text
        }
    }
    # send an HTTP request back to FB
    fb_response = requests.post('https://graph.facebook.com/v10.0/me/messages',
                                params={"access_token": ACCESS_TOKEN},
                                data=json.dumps(question_en),
                                headers={'content-type': 'application/json'})

    if not fb_response.ok:
        app.logger.debug('Display question_en error. %s: %s' % (fb_response.status_code, fb_response.text))

    text = r.lpop(recipient_id + ":questions_de")
    r.lpop(recipient_id + ":questions_de")  # to remove REDIS_EXPIRE_SECONDS
    question_de = {
        "messaging_type": "UPDATE",
        "recipient": {
            "id": recipient_id
        },
        "message": {
            "text": text
        }
    }
    # send an HTTP request back to FB
    fb_response = requests.post('https://graph.facebook.com/v10.0/me/messages',
                                params={"access_token": ACCESS_TOKEN},
                                data=json.dumps(question_de),
                                headers={'content-type': 'application/json'})

    if not fb_response.ok:
        app.logger.debug('Display question_en error. %s: %s' % (fb_response.status_code, fb_response.text))

    return "success"


def check_answer(recipient_id, text):
    answer = r.lpop(recipient_id + ":answers")
    r.lpop(recipient_id + ":answers")  # to remove REDIS_EXPIRE_SECONDS
    if text == answer:
        feedback_text = "Correct!"
        r.incr(recipient_id + ":correct")
    else:
        feedback_text = 'I\'m afarid that\'s not quite right. The correct answer is "{}".'.format(answer)

    feedback = {
        "messaging_type": "UPDATE",
        "recipient": {
            "id": recipient_id
        },
        "message": {
            "text": feedback_text
        }
    }
    # send an HTTP request back to FB
    fb_response = requests.post('https://graph.facebook.com/v10.0/me/messages',
                                params={"access_token": ACCESS_TOKEN},
                                data=json.dumps(feedback),
                                headers={'content-type': 'application/json'})

    if not fb_response.ok:
        app.logger.debug('Post answer feedback error. %s: %s' % (fb_response.status_code, fb_response.text))

    if r.get(recipient_id + ":current") == r.get(recipient_id + ":total"):
        # quiz has ended
        correct = r.get(recipient_id + ":correct")
        total = r.get(recipient_id + ":total")
        quiz_stats = {
            "messaging_type": "UPDATE",
            "recipient": {
                "id": recipient_id
            },
            "message": {
                "text": "Quiz completed! :) Your score is {}/{}.".format(correct, total)
            }
        }
        # send an HTTP request back to FB
        fb_response = requests.post('https://graph.facebook.com/v10.0/me/messages',
                                    params={"access_token": ACCESS_TOKEN},
                                    data=json.dumps(quiz_stats),
                                    headers={'content-type': 'application/json'})

        if not fb_response.ok:
            app.logger.debug('Post end quiz stats error. %s: %s' % (fb_response.status_code, fb_response.text))

        # clear quiz
        clear_quiz_in_redis(recipient_id)

    else:
        post_question(recipient_id)
    return "success"


def process_postback(recipient_id, message):
    payload = message['postback']['payload']
    if payload == 'get_started_payload':
        respond_to_get_started(recipient_id)
    else:
        app.logger.debug('Received unknown postback payload.')
        pass


def process_quick_reply(recipient_id, message):
    payload = message['message']['quick_reply']['payload']
    if payload == 'start_quiz_payload':
        respond_to_start_quiz(recipient_id)


def respond_to_get_started(recipient_id):
    intro_quick_reply = {
      "recipient": {
        "id": recipient_id
      },
      "messaging_type": "RESPONSE",
      "message": {
        "text": "Welcome! I am here to help you build vocabulary in German.",
        "quick_replies": [
            {
                "content_type": "text",
                "title": "Quiz",
                "payload": "start_quiz_payload",
            }
        ]
      }
    }
    # send an HTTP request back to FB
    fb_response = requests.post('https://graph.facebook.com/v10.0/me/messages',
                                params={"access_token": ACCESS_TOKEN},
                                data=json.dumps(intro_quick_reply),
                                headers={'content-type': 'application/json'})

    if not fb_response.ok:
        app.logger.debug('Respond to get started error. %s: %s' % (fb_response.status_code, fb_response.text))

    clear_quiz_in_redis(recipient_id)

    return "success"


def respond_to_start_quiz(recipient_id):
    text = 'To start a quiz, Upload a csv file with a list of words, or send e.g. "Input: eindeutig, Botschaft"'
    start_quiz_prompt = {
        "messaging_type": "RESPONSE",
        "recipient": {
            "id": recipient_id
        },
        "message": {
            "text": text
        }
    }
    # send an HTTP request back to FB
    fb_response = requests.post('https://graph.facebook.com/v10.0/me/messages',
                                params={"access_token": ACCESS_TOKEN},
                                data=json.dumps(start_quiz_prompt),
                                headers={'content-type': 'application/json'})

    if not fb_response.ok:
        app.logger.debug('Display start quiz prompt error. %s: %s' % (fb_response.status_code, fb_response.text))

    # change user mode to quiz
    r.set(recipient_id + ":mode", "quiz", REDIS_EXPIRE_SECONDS)

    return "success"


# Add description here about this if statement.
if __name__ == "__main__":
    app.run()
