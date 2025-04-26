from flask import Flask, request, jsonify
from models import db, Skill, User
import os

app = Flask(__name__)

# Configure SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///coinnect.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

@app.route('/')
def home():
    return "Welcome to Coinnect - Decentralized Skill Sharing Platform!"

@app.route('/register', methods=['POST'])
def register_user():
    data = request.get_json()

    # Check if the email already exists
    existing_user = User.query.filter_by(email=data['email']).first()
    if existing_user:
        return jsonify({'message': 'Email already registered!'}), 400

    new_user = User(
        name=data['name'],
        email=data['email'],
        trust_score=5.0  # Default trust score
    )
    db.session.add(new_user)
    db.session.commit()

    # Register skills the user offers/requested
    for skill_data in data['skills']:
        new_skill = Skill(
            skill_name=skill_data['name'],
            user_id=new_user.id,
            availability=skill_data.get('availability', 'anytime'),
            is_offered=skill_data['is_offered']
        )
        db.session.add(new_skill)

    db.session.commit()
    return jsonify({'message': 'User registered successfully!', 'user_id': new_user.id})

@app.route('/users', methods=['GET'])
def get_users():
    users = User.query.all()
    user_list = []

    for user in users:
        skills = Skill.query.filter_by(user_id=user.id).all()
        skills_data = [
            {
                'skill_name': skill.skill_name,
                'is_offered': skill.is_offered,
                'availability': skill.availability
            } for skill in skills
        ]

        user_list.append({
            'id': user.id,
            'name': user.name,
            'email': user.email,
            'trust_score': user.trust_score,
            'skillcoins_balance': user.skillcoins_balance,
            'skills': skills_data
        })

    return jsonify(user_list)

# Run the app and create tables automatically
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
