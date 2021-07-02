from flask import Flask
from flask_restful import Resource, Api, reqparse, inputs
import hashlib
import json

app = Flask(__name__)
api = Api(app)

class Honor(Resource):
  '''Determines whether the given input has honor or not.'''

  def __init__(self):
    with open('data/memory.json', 'r') as fh:
      self.memory = json.load(fh)

  def _save_honor(self):
    with open('data/memory.json', 'w') as fh:
      fh.write(json.dumps(self.memory))

  def _get_honor(self, topic):
    '''Returns True if the phrase is honorable, False otherwise.'''
    if topic in self.memory['honor']:
      return True
    if topic in self.memory['dishonor']:
      return False

    hasher = hashlib.md5()
    hasher.update(topic.encode('utf-8'))
    if hasher.hexdigest()[-1] in ['0', '1', '2', '3', '4', '5', '6', '7']:
      return True

    return False

  def get(self):
    '''Returns a phrase describing the honor of the input.'''
    parser = reqparse.RequestParser()
    parser.add_argument('phrase', required=True)
    args = parser.parse_args()

    if self._get_honor(args.phrase.lower()):
      return f'{args.phrase} has honor.', 200

    return f'{args.phrase} is without honor.', 200

  def post(self):
    '''Adds a phrase to the known list of honorable/dishonorable phrases.'''
    parser = reqparse.RequestParser()
    parser.add_argument('phrase', required=True)
    parser.add_argument('is_honorable', required=True, type=inputs.boolean)
    args = parser.parse_args()

    topic = args.phrase.lower()

    if args.is_honorable:
      if topic not in self.memory['honor']:
        self.memory['honor'].append(topic)

      if topic in self.memory['dishonor']:
        self.memory['dishonor'].remove(topic)
    else:
      # Not honorable!
      if topic not in self.memory['dishonor']:
        self.memory['dishonor'].append(topic)

      if topic in self.memory['honor']:
        self.memory['honor'].remove(topic)

    self._save_honor()
    if args.is_honorable:
      return f'{args.phrase} will be remembered as honorable.', 200

    return f'{args.phrase} will be remembered as dishonorable.', 200

  def delete(self):
    '''Deletes a phrase from the known list of honorable/dishonorable phrases.'''
    parser = reqparse.RequestParser()
    parser.add_argument('phrase', required=True)
    args = parser.parse_args()

    topic = args.phrase.lower()
    if topic in self.memory['honor']:
      self.memory['honor'].remove(topic)
    if topic in self.memory['dishonor']:
      self.memory['dishonor'].remove(topic)

    self._save_honor()
    return f'{args.phrase} has been forgotten', 200

api.add_resource(Honor, '/honor')

if __name__ == '__main__':
  app.run()
