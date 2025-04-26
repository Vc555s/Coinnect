from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from models import db, User, Skill, Transaction, TrustScore
from ipfs_service import IPFSService
import os
import datetime
import json
from config import Config
from flask_migrate import Migrate


app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

app.config.from_object(Config)
db.init_app(app)

migrate = Migrate(app, db)



ipfs_service = IPFSService()


@app.route('/')
def home():
    try:
        return render_template('index.html')
    except:
        return jsonify({'message': 'API is running. Templates not found.'}), 200
    
@app.route('/ipfs/transaction/<transaction_id>', methods=['GET'])
def get_transaction_from_ipfs(transaction_id):
    try:
        # Get transaction from database
        transaction = Transaction.query.get_or_404(transaction_id)
        
        # If transaction doesn't have an IPFS hash yet, create one
        if not hasattr(transaction, 'ipfs_hash') or not transaction.ipfs_hash:
            # Prepare transaction data
            offerer = User.query.get(transaction.offerer_id)
            requester = User.query.get(transaction.requester_id)
            skill = Skill.query.get(transaction.skill_id)
            
            transaction_data = {
                'id': transaction.id,
                'offerer': offerer.name,
                'requester': requester.name,
                'skill': skill.skill_name if skill else 'Unknown',
                'amount_paid': transaction.amount_paid,
                'transaction_date': transaction.transaction_date.isoformat(),
                'status': transaction.status,
                'timestamp': datetime.datetime.now().isoformat()
            }
            
            # Add to IPFS via Filebase
            ipfs_hash = ipfs_service.add_json_to_ipfs(transaction_data)
            
            if isinstance(ipfs_hash, dict) and 'error' in ipfs_hash:
                return jsonify({'error': ipfs_hash['error']}), 500
            
            # Store the hash in the transaction
            transaction.ipfs_hash = ipfs_hash
            db.session.commit()
            
            # Pin the hash to ensure it persists
            pin_result = ipfs_service.pin_hash(ipfs_hash)
            
            return jsonify({
                'message': 'Transaction added to IPFS',
                'ipfs_hash': ipfs_hash,
                'gateway_url': f"{Config.IPFS_GATEWAY_URL}{ipfs_hash}",
                'transaction_data': transaction_data,
                'pin_result': pin_result
            })
        
        # If transaction already has an IPFS hash, retrieve the data
        ipfs_data = ipfs_service.get_json_from_ipfs(transaction.ipfs_hash)
        
        if isinstance(ipfs_data, dict) and 'error' in ipfs_data:
            return jsonify({'error': ipfs_data['error']}), 500
        
        return jsonify({
            'ipfs_hash': transaction.ipfs_hash,
            'gateway_url': f"{Config.IPFS_GATEWAY_URL}{transaction.ipfs_hash}",
            'transaction_data': ipfs_data
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/ipfs/user/<user_id>', methods=['GET'])
def store_user_profile_on_ipfs(user_id):
    try:
        # Get user from database
        user = User.query.get_or_404(user_id)
        
        # Get skills
        skills = Skill.query.filter_by(user_id=user_id).all()
        skills_data = [{'name': skill.skill_name, 'is_offered': skill.is_offered} for skill in skills]
        
        # Create user profile data
        user_data = {
            'id': user.id,
            'name': user.name,
            'trust_score': user.trust_score,
            'skills': skills_data,
            'timestamp': datetime.datetime.now().isoformat()
        }
        
        # Add to IPFS via Filebase
        ipfs_hash = ipfs_service.add_json_to_ipfs(user_data)
        
        if isinstance(ipfs_hash, dict) and 'error' in ipfs_hash:
            return jsonify({'error': ipfs_hash['error']}), 500
        
        # Store the hash
        user.ipfs_profile_hash = ipfs_hash
        db.session.commit()
        
        # Pin the hash to ensure it persists
        pin_result = ipfs_service.pin_hash(ipfs_hash)
        
        return jsonify({
            'message': 'User profile added to IPFS via Filebase',
            'ipfs_hash': ipfs_hash,
            'gateway_url': f"{Config.IPFS_GATEWAY_URL}{ipfs_hash}",
            'user_data': user_data,
            'pin_result': pin_result
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/register', methods=['GET', 'POST'])
def register_user():
    try:
        if request.method == 'GET':
            try:
                return render_template('register.html')
            except:
                return jsonify({'message': 'Register API endpoint. Use POST to register.'}), 200
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        # Check required fields
        if 'name' not in data or 'email' not in data:
            return jsonify({'error': 'name and email are required'}), 400

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
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/users', methods=['GET'])
def get_users():
    try:
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
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/match_skills', methods=['GET'])
def match_skills():
    try:
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
            if user:  # Make sure user exists
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
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/ipfs/skill/<skill_id>', methods=['GET'])
def store_skill_on_ipfs(skill_id):
    try:
        # Get skill from database
        skill = Skill.query.get_or_404(skill_id)
        user = User.query.get(skill.user_id)
        
        # Create skill metadata
        skill_data = {
            'id': skill.id,
            'name': skill.skill_name,
            'offered_by': user.name,
            'user_id': user.id,
            'is_offered': skill.is_offered,
            'availability': skill.availability,
            'timestamp': datetime.datetime.now().isoformat()
        }
        
        # Add to IPFS via Filebase
        ipfs_hash = ipfs_service.add_json_to_ipfs(skill_data)
        
        if isinstance(ipfs_hash, dict) and 'error' in ipfs_hash:
            return jsonify({'error': ipfs_hash['error']}), 500
        
        # Store the hash
        skill.ipfs_hash = ipfs_hash
        db.session.commit()
        
        # Pin the hash to ensure it persists
        pin_result = ipfs_service.pin_hash(ipfs_hash)
        
        return jsonify({
            'message': 'Skill metadata added to IPFS via Filebase',
            'ipfs_hash': ipfs_hash,
            'gateway_url': f"{Config.IPFS_GATEWAY_URL}{ipfs_hash}",
            'skill_data': skill_data,
            'pin_result': pin_result
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/create_transaction', methods=['POST'])
def create_transaction():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        # Check required fields
        required_fields = ['offerer_id', 'requester_id', 'skill_id', 'amount_paid']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Field {field} is required'}), 400
        
        # Validate transaction data
        offerer = User.query.get(data['offerer_id'])
        requester = User.query.get(data['requester_id'])
        skill = Skill.query.get(data['skill_id'])
        
        if not offerer or not requester or not skill:
            return jsonify({'error': 'Invalid user or skill IDs'}), 400
        
        # Verify the skill belongs to the offerer
        if skill.user_id != data['offerer_id']:
            return jsonify({'error': 'This skill does not belong to the specified offerer'}), 400
        
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
        
        # Store transaction on IPFS via Filebase
        transaction_data = {
            'id': new_transaction.id,
            'offerer': offerer.name,
            'requester': requester.name,
            'skill': skill.skill_name,
            'amount_paid': data['amount_paid'],
            'transaction_date': datetime.datetime.now().isoformat(),
            'status': 'completed',
            'timestamp': datetime.datetime.now().isoformat()
        }
        
        # Add to IPFS and pin
        ipfs_hash = ipfs_service.add_json_to_ipfs(transaction_data)
        
        if isinstance(ipfs_hash, dict) and 'error' in ipfs_hash:
            return jsonify({'error': ipfs_hash['error']}), 500
            
        new_transaction.ipfs_hash = ipfs_hash
        db.session.commit()
        
        # Pin the hash
        ipfs_service.pin_hash(ipfs_hash)
        
        return jsonify({
            'message': 'Transaction successful',
            'transaction_id': new_transaction.id,
            'ipfs_hash': ipfs_hash,
            'ipfs_gateway_url': f"{Config.IPFS_GATEWAY_URL}{ipfs_hash}"
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/verify/transaction/<ipfs_hash>', methods=['GET'])
def verify_transaction(ipfs_hash):
    try:
        # Try to retrieve transaction from IPFS via Filebase
        ipfs_data = ipfs_service.get_json_from_ipfs(ipfs_hash)
        
        if isinstance(ipfs_data, dict) and 'error' in ipfs_data:
            return jsonify({'verified': False, 'error': ipfs_data['error']}), 404
        
        # Check if transaction exists in database
        transaction = Transaction.query.filter_by(ipfs_hash=ipfs_hash).first()
        
        if not transaction:
            return jsonify({
                'verified': False,
                'message': 'Transaction exists on IPFS but not in local database',
                'ipfs_data': ipfs_data
            })
        
        # Verify that the transaction details match
        offerer = User.query.get(transaction.offerer_id)
        requester = User.query.get(transaction.requester_id)
        skill = Skill.query.get(transaction.skill_id)
        
        verification = {
            'database_record': {
                'id': transaction.id,
                'offerer': offerer.name,
                'requester': requester.name,
                'skill': skill.skill_name if skill else 'Unknown',
                'amount_paid': float(transaction.amount_paid),
                'status': transaction.status
            },
            'ipfs_record': ipfs_data,
            'gateway_url': f"{Config.IPFS_GATEWAY_URL}{ipfs_hash}",
            'verified': True
        }
        
        return jsonify(verification)
    except Exception as e:
        return jsonify({'verified': False, 'error': str(e)}), 500

@app.route('/search_skills', methods=['GET'])
def search_skills():
    try:
        skill_type = request.args.get('type', 'offered')  # 'offered' or 'requested'
        skill_name = request.args.get('name', '')
        
        # Filter by is_offered based on type parameter
        is_offered = True if skill_type == 'offered' else False
        
        query = Skill.query.filter_by(is_offered=is_offered)
        
        # Add skill name filter if provided
        if skill_name:
            query = query.filter(Skill.skill_name.like(f'%{skill_name}%'))
        
        skills = query.all()
        
        if not skills:
            return jsonify([]), 200  # Return empty array rather than potential error
        
        result = []
        for skill in skills:
            user = User.query.get(skill.user_id)
            if user:  # Make sure user exists
                result.append({
                    'skill_id': skill.id,
                    'skill_name': skill.skill_name,
                    'user_id': user.id,
                    'user_name': user.name,
                    'availability': skill.availability,
                    'trust_score': user.trust_score
                })
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/user/<int:user_id>', methods=['GET'])
def get_user_profile(user_id):
    try:
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
        
        # Sort transactions by date (newest first)
        transaction_history.sort(key=lambda x: x['date'], reverse=True)
        
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
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/skill', methods=['POST'])
def add_skill():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        # Check required fields
        if 'skill_name' not in data or 'user_id' not in data:
            return jsonify({'error': 'skill_name and user_id are required'}), 400
        
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
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/skill/<int:skill_id>', methods=['PUT', 'DELETE'])
def manage_skill(skill_id):
    try:
        skill = Skill.query.get_or_404(skill_id)
        
        if request.method == 'DELETE':
            db.session.delete(skill)
            db.session.commit()
            return jsonify({'message': 'Skill deleted successfully'})
        
        # If PUT request
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
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
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/check_fraud', methods=['GET'])
def check_fraud():
    try:
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
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/dashboard', methods=['GET'])
def dashboard():
    try:
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
        
        try:
            return render_template('dashboard.html', 
                                  user_count=user_count,
                                  skill_count=skill_count,
                                  transaction_count=transaction_count,
                                  popular_skills=popular_skills,
                                  sought_skills=sought_skills,
                                  active_users=active_users)
        except:
            # If template not found, return JSON
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
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/rate_transaction/<int:transaction_id>', methods=['POST'])
def rate_transaction(transaction_id):
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
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
        
        # Check if this transaction has already been rated by this party
        existing_rating = TrustScore.query.filter_by(
            transaction_id=transaction_id,
            user_id=user_id
        ).first()
        
        if existing_rating:
            return jsonify({'error': 'This transaction has already been rated'}), 400
        
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
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/recommendations/<int:user_id>', methods=['GET'])
def get_recommendations(user_id):
    try:
        # Check if user exists
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
            
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
                    if user:  # Make sure user exists
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
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def init_db():
    """Initialize the database with sample data"""
    # Only add data if the database is empty
    if User.query.count() == 0:
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
    try:
        with app.app_context():
            db.create_all()
            init_db()
        return jsonify({'message': 'Database initialized with sample data'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/docs')
def api_docs():
    try:
        return render_template('docs.html')
    except:
        return jsonify({
            'message': 'API documentation not available as HTML. Here are the available endpoints:',
            'endpoints': [
                '/register - Register new user (POST)',
                '/users - Get all users (GET)',
                '/match_skills - Match skills (GET)',
                '/search_skills - Search for skills (GET)',
                '/user/<id> - Get user profile (GET)',
                '/skill - Add skill (POST)',
                '/skill/<id> - Manage skill (PUT, DELETE)',
                '/create_transaction - Create a transaction (POST)',
                '/rate_transaction/<id> - Rate a transaction (POST)',
                '/recommendations/<id> - Get recommendations (GET)',
                '/dashboard - Get system statistics (GET)',
                '/check_fraud - Check for suspicious users (GET)',
                '/setup_db - Setup database with sample data (GET)'
            ]
        })

# Run the app and create tables automatically
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        init_db()  # Initialize with sample data if needed
    app.run(debug=True)
