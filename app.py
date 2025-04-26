from flask import Flask, request, jsonify, render_template
from models import db, User, Skill, Transaction, TrustScore
import os

app = Flask(__name__)

# Configure SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///coinnect.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register_user():
    if request.method == 'GET':
        return render_template('register.html')
    
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
    if 'skills' in data:
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

@app.route('/match_skills', methods=['GET'])
def match_skills():
    # Get skill requested by the user
    requested_skill = request.args.get('skill_name')
    
    if not requested_skill:
        return jsonify({'error': 'Please provide a skill_name parameter'}), 400
    
    # Find users offering this skill
    matching_skills = Skill.query.filter_by(
        skill_name=requested_skill, 
        is_offered=True
    ).all()
    
    matches = []
    for skill in matching_skills:
        user = User.query.get(skill.user_id)
        matches.append({
            'user_id': user.id,
            'name': user.name,
            'trust_score': user.trust_score,
            'availability': skill.availability
        })
    
    # Sort matches by trust score (higher score first)
    matches.sort(key=lambda x: x['trust_score'], reverse=True)
    
    return jsonify({
        'requested_skill': requested_skill,
        'matches': matches
    })

@app.route('/create_transaction', methods=['POST'])
def create_transaction():
    data = request.get_json()
    
    # Validate transaction data
    offerer = User.query.get(data['offerer_id'])
    requester = User.query.get(data['requester_id'])
    skill = Skill.query.get(data['skill_id'])
    
    if not offerer or not requester or not skill:
        return jsonify({'error': 'Invalid user or skill IDs'}), 400
    
    # Check if requester has enough SkillCoins
    if requester.skillcoins_balance < data['amount_paid']:
        return jsonify({'error': 'Insufficient SkillCoins balance'}), 400
    
    # Create transaction
    new_transaction = Transaction(
        offerer_id=data['offerer_id'],
        requester_id=data['requester_id'],
        skill_id=data['skill_id'],
        amount_paid=data['amount_paid']
    )
    
    # Transfer coins from requester to offerer
    requester.skillcoins_balance -= data['amount_paid']
    offerer.skillcoins_balance += data['amount_paid']
    
    # Update trust scores (simple increment)
    offerer.trust_score += 0.1
    requester.trust_score += 0.05
    
    db.session.add(new_transaction)
    db.session.commit()
    
    return jsonify({
        'message': 'Transaction successful',
        'transaction_id': new_transaction.id
    })

@app.route('/search_skills', methods=['GET'])
def search_skills():
    skill_type = request.args.get('type', 'offered')  # 'offered' or 'requested'
    skill_name = request.args.get('name', '')
    
    # Filter by is_offered based on type parameter
    is_offered = True if skill_type == 'offered' else False
    
    query = Skill.query.filter_by(is_offered=is_offered)
    
    # Add skill name filter if provided
    if skill_name:
        query = query.filter(Skill.skill_name.like(f'%{skill_name}%'))
    
    skills = query.all()
    
    result = []
    for skill in skills:
        user = User.query.get(skill.user_id)
        result.append({
            'skill_id': skill.id,
            'skill_name': skill.skill_name,
            'user_id': user.id,
            'user_name': user.name,
            'availability': skill.availability,
            'trust_score': user.trust_score
        })
    
    return jsonify(result)

@app.route('/user/<int:user_id>', methods=['GET'])
def get_user_profile(user_id):
    user = User.query.get_or_404(user_id)
    
    # Get skills offered by this user
    offered_skills = Skill.query.filter_by(user_id=user_id, is_offered=True).all()
    offered_skills_data = [
        {
            'id': skill.id,
            'name': skill.skill_name,
            'availability': skill.availability
        } for skill in offered_skills
    ]
    
    # Get skills requested by this user
    requested_skills = Skill.query.filter_by(user_id=user_id, is_offered=False).all()
    requested_skills_data = [
        {
            'id': skill.id,
            'name': skill.skill_name
        } for skill in requested_skills
    ]
    
    # Get transaction history
    given_transactions = Transaction.query.filter_by(offerer_id=user_id).all()
    received_transactions = Transaction.query.filter_by(requester_id=user_id).all()
    
    transaction_history = []
    for tx in given_transactions + received_transactions:
        skill = Skill.query.get(tx.skill_id)
        transaction_history.append({
            'id': tx.id,
            'date': tx.transaction_date.strftime('%Y-%m-%d %H:%M:%S'),
            'skill': skill.skill_name if skill else 'Unknown',
            'amount': tx.amount_paid,
            'type': 'given' if tx.offerer_id == user_id else 'received'
        })
    
    return jsonify({
        'id': user.id,
        'name': user.name,
        'email': user.email,
        'trust_score': user.trust_score,
        'skillcoins_balance': user.skillcoins_balance,
        'offered_skills': offered_skills_data,
        'requested_skills': requested_skills_data,
        'transaction_history': transaction_history
    })

@app.route('/skill', methods=['POST'])
def add_skill():
    data = request.get_json()
    
    # Validate user exists
    user = User.query.get(data['user_id'])
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Check for sudden skill increase (fraud detection)
    current_skill_count = Skill.query.filter_by(user_id=data['user_id'], is_offered=True).count()
    if current_skill_count >= 5:
        # Flag for potential fraud review but still allow
        print(f"POTENTIAL FRAUD: User {data['user_id']} adding many skills")
    
    new_skill = Skill(
        skill_name=data['skill_name'],
        user_id=data['user_id'],
        is_offered=data.get('is_offered', True),
        availability=data.get('availability', 'anytime')
    )
    
    db.session.add(new_skill)
    db.session.commit()
    
    return jsonify({
        'message': 'Skill added successfully',
        'skill_id': new_skill.id
    })

@app.route('/skill/<int:skill_id>', methods=['PUT', 'DELETE'])
def manage_skill(skill_id):
    skill = Skill.query.get_or_404(skill_id)
    
    if request.method == 'DELETE':
        db.session.delete(skill)
        db.session.commit()
        return jsonify({'message': 'Skill deleted successfully'})
    
    # If PUT request
    data = request.get_json()
    
    if 'skill_name' in data:
        skill.skill_name = data['skill_name']
    if 'availability' in data:
        skill.availability = data['availability']
    if 'is_offered' in data:
        skill.is_offered = data['is_offered']
    
    db.session.commit()
    
    return jsonify({
        'message': 'Skill updated successfully',
        'skill': {
            'id': skill.id,
            'name': skill.skill_name,
            'is_offered': skill.is_offered,
            'availability': skill.availability
        }
    })

@app.route('/check_fraud', methods=['GET'])
def check_fraud():
    # Get all users
    users = User.query.all()
    
    suspicious_users = []
    for user in users:
        # Check if user has too many skills without transactions
        skill_count = Skill.query.filter_by(user_id=user.id, is_offered=True).count()
        transaction_count = Transaction.query.filter_by(offerer_id=user.id).count()
        
        # If user claims more than 5 skills but has no transactions
        if skill_count > 5 and transaction_count == 0:
            suspicious_users.append({
                'user_id': user.id,
                'name': user.name,
                'skill_count': skill_count,
                'transaction_count': transaction_count,
                'reason': 'Many skills claimed but no transaction history'
            })
        
        # If user has very low trust score
        if user.trust_score < 3.0:
            suspicious_users.append({
                'user_id': user.id,
                'name': user.name,
                'trust_score': user.trust_score,
                'reason': 'Low trust score'
            })
    
    return jsonify({
        'suspicious_users': suspicious_users,
        'count': len(suspicious_users)
    })

@app.route('/dashboard', methods=['GET'])
def dashboard():
    # Count total users, skills and transactions
    user_count = User.query.count()
    skill_count = Skill.query.count() 
    transaction_count = Transaction.query.count()
    
    # Get most popular skills (offered by multiple users)
    popular_skills = db.session.query(
        Skill.skill_name, 
        db.func.count(Skill.id).label('count')
    ).filter_by(is_offered=True).group_by(
        Skill.skill_name
    ).order_by(db.desc('count')).limit(5).all()
    
    # Get most sought-after skills (requested by multiple users)
    sought_skills = db.session.query(
        Skill.skill_name, 
        db.func.count(Skill.id).label('count')
    ).filter_by(is_offered=False).group_by(
        Skill.skill_name
    ).order_by(db.desc('count')).limit(5).all()
    
    # Get most active users (by transaction count)
    active_users = db.session.query(
        User.id, User.name,
        db.func.count(Transaction.id).label('tx_count')
    ).outerjoin(
        Transaction, 
        (User.id == Transaction.offerer_id) | (User.id == Transaction.requester_id)
    ).group_by(User.id).order_by(db.desc('tx_count')).limit(5).all()
    
    return jsonify({
        'stats': {
            'users': user_count,
            'skills': skill_count,
            'transactions': transaction_count
        },
        'popular_skills': [{'name': skill[0], 'count': skill[1]} for skill in popular_skills],
        'sought_skills': [{'name': skill[0], 'count': skill[1]} for skill in sought_skills],
        'active_users': [{'id': user[0], 'name': user[1], 'transactions': user[2]} for user in active_users]
    })

@app.route('/rate_transaction/<int:transaction_id>', methods=['POST'])
def rate_transaction(transaction_id):
    data = request.get_json()
    transaction = Transaction.query.get_or_404(transaction_id)
    
    # Get rating score (1-5)
    rating = data.get('rating', 5)
    if rating < 1 or rating > 5:
        return jsonify({'error': 'Rating must be between 1 and 5'}), 400
    
    # Who's rating whom
    is_requester_rating = data.get('is_requester_rating', True)
    
    # Create trust score entry
    if is_requester_rating:
        # Requester is rating the offerer
        user_id = transaction.offerer_id
    else:
        # Offerer is rating the requester
        user_id = transaction.requester_id
    
    trust_score_entry = TrustScore(
        user_id=user_id,
        transaction_id=transaction.id,
        score=rating,
        feedback=data.get('feedback', '')
    )
    db.session.add(trust_score_entry)
    
    # Update user's trust score (weighted average)
    user = User.query.get(user_id)
    user.trust_score = (0.9 * user.trust_score) + (0.1 * rating)
    
    db.session.commit()
    
    return jsonify({
        'message': 'Rating submitted successfully',
        'new_trust_score': user.trust_score
    })

@app.route('/recommendations/<int:user_id>', methods=['GET'])
def get_recommendations(user_id):
    # Get user's requested skills
    user_requested_skills = Skill.query.filter_by(
        user_id=user_id, 
        is_offered=False
    ).all()
    requested_skill_names = [skill.skill_name for skill in user_requested_skills]
    
    # Find users offering these skills
    relevant_users = []
    for skill_name in requested_skill_names:
        matching_skills = Skill.query.filter_by(
            skill_name=skill_name, 
            is_offered=True
        ).all()
        
        for skill in matching_skills:
            if skill.user_id != user_id:  # Don't recommend the user's own skills
                user = User.query.get(skill.user_id)
                relevant_users.append({
                    'user_id': user.id,
                    'name': user.name,
                    'skill': skill_name,
                    'trust_score': user.trust_score,
                    'availability': skill.availability
                })
    
    # Find similar skills they might be interested in
    skill_recommendations = []
    for relevant_user in relevant_users:
        other_skills = Skill.query.filter_by(
            user_id=relevant_user['user_id'],
            is_offered=True
        ).all()
        
        for skill in other_skills:
            if skill.skill_name not in requested_skill_names:
                skill_recommendations.append({
                    'skill_name': skill.skill_name,
                    'offered_by': relevant_user['name'],
                    'user_id': relevant_user['user_id'],
                    'trust_score': relevant_user['trust_score']
                })
    
    # Remove duplicates and limit to top 5
    unique_recommendations = []
    seen_skills = set()
    for rec in skill_recommendations:
        if rec['skill_name'] not in seen_skills:
            seen_skills.add(rec['skill_name'])
            unique_recommendations.append(rec)
            if len(unique_recommendations) >= 5:
                break
    
    return jsonify({
        'skill_recommendations': unique_recommendations,
        'user_matches': relevant_users[:5]  # Limit to top 5
    })

def init_db():
    """Initialize the database with sample data"""
    # Create some sample users
    user1 = User(name="Alice", email="alice@example.com")
    user2 = User(name="Bob", email="bob@example.com")
    user3 = User(name="Charlie", email="charlie@example.com")
    db.session.add_all([user1, user2, user3])
    db.session.commit()
    
    # Create some sample skills
    skills = [
        Skill(skill_name="Python Programming", user_id=1, is_offered=True),
        Skill(skill_name="Graphic Design", user_id=2, is_offered=True),
        Skill(skill_name="Web Development", user_id=3, is_offered=True),
        Skill(skill_name="Data Analysis", user_id=1, is_offered=True),
        Skill(skill_name="UI/UX Design", user_id=2, is_offered=False),
        Skill(skill_name="Machine Learning", user_id=3, is_offered=False)
    ]
    db.session.add_all(skills)
    db.session.commit()
    
    # Create some sample transactions
    transactions = [
        Transaction(offerer_id=1, requester_id=2, skill_id=1, amount_paid=5.0),
        Transaction(offerer_id=2, requester_id=3, skill_id=2, amount_paid=3.0)
    ]
    db.session.add_all(transactions)
    db.session.commit()

@app.route('/setup_db', methods=['GET'])
def setup_database():
    """Route to initialize the database (for development only)"""
    with app.app_context():
        db.create_all()
        init_db()
    return jsonify({'message': 'Database initialized with sample data'})

@app.route('/docs')
def api_docs():
    return render_template('docs.html')

# Run the app and create tables automatically
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
