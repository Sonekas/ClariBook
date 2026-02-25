from typing import Any, Dict
import logging
from flask import Blueprint, jsonify, request
from src.models.user import User, db

logger = logging.getLogger(__name__)
user_bp = Blueprint('user', __name__)


@user_bp.route('/users', methods=['GET'])
def get_users():
    users = User.query.all()
    return jsonify([user.to_dict() for user in users])


@user_bp.route('/users', methods=['POST'])
def create_user():
    data: Dict[str, Any] = request.get_json() or {}
    username = data.get('username')
    email = data.get('email')
    if not username or not email:
        return jsonify({'error': 'username and email are required'}), 400

    try:
        user = User(username=username, email=email)
        db.session.add(user)
        db.session.commit()
        return jsonify(user.to_dict()), 201
    except Exception:
        logger.exception('Erro criando usuário')
        db.session.rollback()
        return jsonify({'error': 'Erro interno'}), 500


@user_bp.route('/users/<int:user_id>', methods=['GET'])
def get_user(user_id: int):
    user = User.query.get_or_404(user_id)
    return jsonify(user.to_dict())


@user_bp.route('/users/<int:user_id>', methods=['PUT'])
def update_user(user_id: int):
    user = User.query.get_or_404(user_id)
    data: Dict[str, Any] = request.get_json() or {}
    user.username = data.get('username', user.username)
    user.email = data.get('email', user.email)
    try:
        db.session.commit()
        return jsonify(user.to_dict())
    except Exception:
        logger.exception('Erro atualizando usuário %s', user_id)
        db.session.rollback()
        return jsonify({'error': 'Erro interno'}), 500


@user_bp.route('/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id: int):
    user = User.query.get_or_404(user_id)
    try:
        db.session.delete(user)
        db.session.commit()
        return '', 204
    except Exception:
        logger.exception('Erro deletando usuário %s', user_id)
        db.session.rollback()
        return jsonify({'error': 'Erro interno'}), 500
