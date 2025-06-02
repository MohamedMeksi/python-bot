import json
import os
from datetime import datetime
from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage, AssistantMessage
from azure.core.credentials import AzureKeyCredential
from dotenv import load_dotenv
import hashlib
import re

# Charger les variables d'environnement
load_dotenv()

class SmartConversationMemory:
    """Système de mémoire intelligent avec reconnaissance automatique des utilisateurs"""
    
    def __init__(self, storage_file="smart_conversations.json"):
        self.storage_file = storage_file
        self.conversations = self._load_all_conversations()
        print(f"📁 Mémoire chargée: {os.path.abspath(self.storage_file)}")
    
    def _load_all_conversations(self):
        """Charge toutes les conversations depuis le fichier JSON"""
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    conversations = data.get('conversations', {})
                    print(f"✅ {len(conversations)} utilisateurs chargés")
                    return conversations
            except Exception as e:
                print(f"❌ Erreur chargement: {e}")
                return {}
        return {}
    
    def _save_all_conversations(self):
        """Sauvegarde avec métadonnées"""
        try:
            backup_data = {
                "last_updated": datetime.now().isoformat(),
                "total_users": len(self.conversations),
                "conversations": self.conversations
            }
            
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"❌ Erreur sauvegarde: {e}")
    
    def is_existing_user(self, user_id):
        """Vérifie si l'utilisateur existe déjà"""
        exists = user_id in self.conversations
        print(f"🔍 Utilisateur {user_id}: {'EXISTANT' if exists else 'NOUVEAU'}")
        return exists
    
    def get_user_basic_info(self, user_id):
        """Récupère les informations de base de l'utilisateur"""
        if user_id in self.conversations:
            user_data = self.conversations[user_id]
            basic_info = user_data.get('basic_info', {})
            
            print(f"👤 Info utilisateur {user_id}:")
            for key, value in basic_info.items():
                print(f"   - {key}: {value}")
                
            return basic_info
        return {}
    
    def create_new_user_profile(self, user_id):
        """Crée un nouveau profil utilisateur"""
        user_data = {
            "user_id": user_id,
            "created_at": datetime.now().isoformat(),
            "last_active": datetime.now().isoformat(),
            "is_first_conversation": True,
            "basic_info": {},
            "learning_phase": True,
            "total_messages": 0,
            "conversation_sessions": 0,
            "messages": [],
            "preferences": {},
            "personality_traits": []
        }
        
        self.conversations[user_id] = user_data
        self._save_all_conversations()
        print(f"🆕 Nouveau profil créé pour: {user_id}")
        return user_data
    
    def update_basic_info(self, user_id, new_info):
        """Met à jour les informations de base de l'utilisateur"""
        if user_id not in self.conversations:
            self.create_new_user_profile(user_id)
        
        user_data = self.conversations[user_id]
        user_data['basic_info'].update(new_info)
        user_data['last_active'] = datetime.now().isoformat()
        
        # Marquer la phase d'apprentissage comme terminée après quelques infos
        if len(user_data['basic_info']) >= 3:
            user_data['learning_phase'] = False
            print(f"🎓 Phase d'apprentissage terminée pour {user_id}")
        
        self._save_all_conversations()
        print(f"📝 Infos mises à jour pour {user_id}: {new_info}")
    
    def add_conversation_exchange(self, user_id, user_message, ai_response, extracted_info=None):
        """Ajoute un échange de conversation avec extraction d'infos"""
        if user_id not in self.conversations:
            self.create_new_user_profile(user_id)
        
        user_data = self.conversations[user_id]
        
        # Mettre à jour les statistiques
        user_data['total_messages'] += 2
        user_data['last_active'] = datetime.now().isoformat()
        
        # Si c'est la première conversation, l'indiquer
        if user_data.get('is_first_conversation', False):
            user_data['is_first_conversation'] = False
            user_data['conversation_sessions'] = 1
            print(f"🌟 Première conversation avec {user_id}")
        
        # Ajouter l'échange
        exchange = {
            "exchange_id": len(user_data['messages']) + 1,
            "timestamp": datetime.now().isoformat(),
            "user_message": {
                "content": user_message,
                "timestamp": datetime.now().isoformat()
            },
            "ai_response": {
                "content": ai_response,
                "timestamp": datetime.now().isoformat()
            }
        }
        
        user_data['messages'].append(exchange)
        
        # Extraire et sauvegarder les nouvelles informations
        if extracted_info:
            self.update_basic_info(user_id, extracted_info)
        
        self._save_all_conversations()
    
    def get_conversation_context(self, user_id, max_messages=10):
        """Récupère le contexte de conversation pour l'IA"""
        if user_id not in self.conversations:
            return []
        
        user_data = self.conversations[user_id]
        messages = []
        
        # Prendre les derniers échanges
        recent_exchanges = user_data['messages'][-max_messages:] if user_data['messages'] else []
        
        for exchange in recent_exchanges:
            messages.append(UserMessage(content=exchange['user_message']['content']))
            messages.append(AssistantMessage(content=exchange['ai_response']['content']))
        
        return messages
    
    def get_personalized_greeting(self, user_id):
        """Génère un message de salutation personnalisé"""
        if not self.is_existing_user(user_id):
            return "Bonjour! Je ne vous connais pas encore. Pouvez-vous me dire votre nom?"
        
        user_data = self.conversations[user_id]
        basic_info = user_data.get('basic_info', {})
        
        # Construire le message personnalisé
        name = basic_info.get('nom', basic_info.get('name', ''))
        profession = basic_info.get('profession', basic_info.get('job', ''))
        last_active = user_data.get('last_active', '')
        
        greeting_parts = []
        
        if name:
            greeting_parts.append(f"Bonjour {name}!")
        else:
            greeting_parts.append("Re-bonjour!")
        
        if profession:
            greeting_parts.append(f"Comment ça va dans le {profession}?")
        
        if last_active:
            try:
                last_date = datetime.fromisoformat(last_active.replace('Z', '+00:00'))
                days_ago = (datetime.now() - last_date.replace(tzinfo=None)).days
                if days_ago == 0:
                    greeting_parts.append("On continue notre conversation!")
                elif days_ago == 1:
                    greeting_parts.append("Content de vous revoir après hier!")
                elif days_ago < 7:
                    greeting_parts.append(f"Ça fait {days_ago} jours! Comment allez-vous?")
                else:
                    greeting_parts.append("Ça fait longtemps! Quoi de neuf?")
            except:
                pass
        
        return " ".join(greeting_parts)


class IntelligentInfoExtractor:
    """Extracteur intelligent d'informations personnelles"""
    
    @staticmethod
    def extract_personal_info(message):
        """Extrait les informations personnelles d'un message"""
        info = {}
        message_lower = message.lower()
        
        # Extraction du nom
        name_patterns = [
            r"je m['\']appelle\s+(\w+)",
            r"mon nom est\s+(\w+)",
            r"je suis\s+(\w+)",
            r"c['\']est\s+(\w+)",
            r"moi c['\']est\s+(\w+)"
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, message_lower)
            if match:
                info['nom'] = match.group(1).capitalize()
                break
        
        # Extraction de la profession
        job_patterns = [
            r"je travaille (?:en|dans|comme)\s+([^.!?]+)",
            r"je suis\s+(?:un|une)\s+([^.!?]+)",
            r"ma profession est\s+([^.!?]+)",
            r"je fais\s+([^.!?]+)",
            r"mon métier est\s+([^.!?]+)"
        ]
        
        for pattern in job_patterns:
            match = re.search(pattern, message_lower)
            if match:
                job = match.group(1).strip()
                if len(job) > 2 and len(job) < 50:  # Validation basique
                    info['profession'] = job
                break
        
        # Extraction de l'âge
        age_patterns = [
            r"j['\']ai\s+(\d+)\s+ans",
            r"age[^\d]*(\d+)",
            r"(\d+)\s+ans"
        ]
        
        for pattern in age_patterns:
            match = re.search(pattern, message_lower)
            if match:
                age = int(match.group(1))
                if 10 <= age <= 100:  # Validation d'âge raisonnable
                    info['age'] = age
                break
        
        # Extraction de la ville
        city_patterns = [
            r"j['\']habite à\s+([^.!?]+)",
            r"je vis à\s+([^.!?]+)",
            r"je suis de\s+([^.!?]+)",
            r"ma ville est\s+([^.!?]+)"
        ]
        
        for pattern in city_patterns:
            match = re.search(pattern, message_lower)
            if match:
                city = match.group(1).strip()
                if len(city) > 1 and len(city) < 30:
                    info['ville'] = city.title()
                break
        
        # Extraction des hobbies/intérêts
        hobby_patterns = [
            r"j['\']aime\s+([^.!?]+)",
            r"mes hobbies sont\s+([^.!?]+)",
            r"je pratique\s+([^.!?]+)",
            r"mon passe-temps est\s+([^.!?]+)"
        ]
        
        for pattern in hobby_patterns:
            match = re.search(pattern, message_lower)
            if match:
                hobby = match.group(1).strip()
                if len(hobby) > 2 and len(hobby) < 100:
                    info['hobbies'] = hobby
                break
        
        return info


class SmartAzureAIAgent:
    """Agent Azure AI intelligent avec reconnaissance et apprentissage automatique"""
    
    def __init__(self, endpoint=None, api_key=None, model_name="gpt-4o"):
        # Configuration Azure
        self.endpoint = os.getenv("AZURE_INFERENCE_ENDPOINT")
        self.api_key = os.getenv("AZURE_INFERENCE_KEY")
        self.model_name = os.getenv("DEPLOYMENT_NAME")
        
        if not self.endpoint or not self.api_key:
            raise ValueError("❌ Variables Azure manquantes dans .env")
        
        # Client Azure AI
        self.client = ChatCompletionsClient(
            endpoint=self.endpoint,
            credential=AzureKeyCredential(self.api_key)
        )
        
        # Système de mémoire intelligent
        self.memory = SmartConversationMemory()
        self.info_extractor = IntelligentInfoExtractor()
        
        print("🤖 Agent Azure AI Intelligent activé!")
    
    def _generate_user_id(self, identifier):
        """Génère un ID stable pour l'utilisateur"""
        return hashlib.md5(str(identifier).encode()).hexdigest()[:10]
    
    def _create_system_prompt(self, user_id, is_new_user, basic_info):
        """Crée un prompt système personnalisé selon l'utilisateur"""
        
        if is_new_user:
            return """Tu es un assistant IA amical qui rencontre ce nouveau utilisateur pour la première fois.
            
            PHASE D'APPRENTISSAGE - Tes objectifs:
            1. Te présenter chaleureusement
            2. Apprendre le nom de l'utilisateur
            3. Découvrir sa profession/occupation
            4. Connaître ses intérêts principaux
            5. Comprendre ses besoins
            
            Sois naturel, curieux mais pas intrusif. Pose UNE question à la fois.
            Montre de l'intérêt pour les réponses et rebondis dessus.
            """
        else:
            # Utilisateur existant - personnaliser selon ses infos
            name = basic_info.get('nom', '')
            profession = basic_info.get('profession', '')
            hobbies = basic_info.get('hobbies', '')
            
            personal_context = f"""Tu connais déjà cet utilisateur:
            - Nom: {name}
            - Profession: {profession}
            - Intérêts: {hobbies}
            """
            
            return f"""Tu es un assistant IA qui a déjà une relation établie avec cet utilisateur.
            
            {personal_context}
            
            INSTRUCTIONS:
            - Salue-le personnellement avec son nom
            - Fais référence à vos conversations précédentes
            - Adapte ton style selon sa personnalité
            - Utilise tes connaissances sur lui pour être plus utile
            - Sois chaleureux comme un ami qui le retrouve
            
            Continue la conversation de manière naturelle et personnalisée.
            """
    
    def smart_chat(self, user_identifier, message):
        """Chat intelligent avec reconnaissance automatique"""
        user_id = self._generate_user_id(user_identifier)
        
        # Vérifier si c'est un nouvel utilisateur
        is_new_user = not self.memory.is_existing_user(user_id)
        
        if is_new_user:
            print(f"🆕 NOUVEAU UTILISATEUR: {user_identifier}")
            user_data = self.memory.create_new_user_profile(user_id)
            basic_info = {}
        else:
            print(f"👋 UTILISATEUR EXISTANT: {user_identifier}")
            basic_info = self.memory.get_user_basic_info(user_id)
            user_data = self.memory.conversations[user_id]
        
        try:
            # Extraire les nouvelles informations du message
            extracted_info = self.info_extractor.extract_personal_info(message)
            if extracted_info:
                print(f"📝 Informations extraites: {extracted_info}")
            
            # Créer le prompt système adapté
            system_prompt = self._create_system_prompt(user_id, is_new_user, basic_info)
            
            # Préparer les messages
            messages = [SystemMessage(content=system_prompt)]
            
            # Ajouter le contexte des conversations précédentes
            if not is_new_user:
                context_messages = self.memory.get_conversation_context(user_id)
                messages.extend(context_messages)
            
            # Ajouter le message actuel
            messages.append(UserMessage(content=message))
            
            # Appeler Azure AI
            response = self.client.complete(
                model=self.model_name,
                messages=messages,
                max_tokens=800,
                temperature=0.8
            )
            
            ai_response = response.choices[0].message.content
            
            # Sauvegarder l'échange avec les infos extraites
            self.memory.add_conversation_exchange(
                user_id=user_id,
                user_message=message,
                ai_response=ai_response,
                extracted_info=extracted_info
            )
            
            return ai_response
            
        except Exception as e:
            error_msg = f"❌ Erreur: {e}"
            print(error_msg)
            return "Désolé, je rencontre un problème technique. Pouvez-vous réessayer?"
    
    def get_smart_greeting(self, user_identifier):
        """Génère une salutation intelligente"""
        user_id = self._generate_user_id(user_identifier)
        return self.memory.get_personalized_greeting(user_id)
    
    def get_user_profile(self, user_identifier):
        """Affiche le profil complet de l'utilisateur"""
        user_id = self._generate_user_id(user_identifier)
        
        if not self.memory.is_existing_user(user_id):
            return "❌ Utilisateur inconnu"
        
        user_data = self.memory.conversations[user_id]
        basic_info = user_data.get('basic_info', {})
        
        profile = f"""
👤 PROFIL UTILISATEUR
==================
🆔 ID: {user_id}
📅 Première rencontre: {user_data.get('created_at', '')[:10]}
🕐 Dernière activité: {user_data.get('last_active', '')[:10]}
💬 Messages échangés: {user_data.get('total_messages', 0)}
🎓 Phase d'apprentissage: {'En cours' if user_data.get('learning_phase') else 'Terminée'}

📋 INFORMATIONS PERSONNELLES:
"""
        
        for key, value in basic_info.items():
            profile += f"   • {key.title()}: {value}\n"
        
        return profile.strip()


def main():
    """Interface de test du système intelligent"""
    
    print("🧠 Système Azure AI Intelligent avec Reconnaissance Automatique")
    print("=" * 70)
    
    try:
        agent = SmartAzureAIAgent()
        
        print("\n💡 Le système reconnaît automatiquement:")
        print("   • Nouveaux utilisateurs → Phase d'apprentissage")
        print("   • Utilisateurs existants → Salutation personnalisée")
        print("   • Extraction automatique d'informations personnelles")
        print("-" * 70)
        
        while True:
            user_input = input("\n🆔 Identifiant utilisateur (ou 'quit'): ").strip()
            
            if user_input.lower() == 'quit':
                break
            
            if not user_input:
                continue
            
            # Afficher la salutation intelligente
            greeting = agent.get_smart_greeting(user_input)
            print(f"\n🤖 {greeting}")
            
            # Boucle de conversation pour cet utilisateur
            while True:
                message = input(f"\n💬 {user_input}: ").strip()
                
                if not message or message.lower() in ['quit', 'exit', 'changer']:
                    break
                
                if message.lower() == 'profile':
                    print(agent.get_user_profile(user_input))
                    continue
                
                # Chat intelligent
                print("🤖 Assistant: ", end="", flush=True)
                response = agent.smart_chat(user_input, message)
                print(response)
            
            print(f"\n👋 À bientôt {user_input}!")
            
    except Exception as e:
        print(f"❌ Erreur: {e}")


# ============================================================================
# EXEMPLE D'UTILISATION COMPLÈTE
# ============================================================================

def demo_complete():
    """Démonstration complète du système"""
    agent = SmartAzureAIAgent()
    
    print("\n=== DÉMONSTRATION ===")
    
    # Première conversation avec un nouveau utilisateur
    print("\n1️⃣ NOUVEAU UTILISATEUR - Marie")
    response1 = agent.smart_chat("marie@email.com", "Bonjour!")
    print("🤖:", response1)
    
    response2 = agent.smart_chat("marie@email.com", "Je m'appelle Marie et je travaille en marketing")
    print("🤖:", response2)
    
    # Utilisateur existant qui revient
    print("\n2️⃣ MARIE REVIENT PLUS TARD")
    greeting = agent.get_smart_greeting("marie@email.com")
    print("🤖:", greeting)
    
    response3 = agent.smart_chat("marie@email.com", "Salut! Tu te souviens de moi?")
    print("🤖:", response3)
    
    # Profil utilisateur
    print("\n3️⃣ PROFIL DE MARIE")
    print(agent.get_user_profile("marie@email.com"))


if __name__ == "__main__":
    main()
    
    # Décommenter pour la démo
    # demo_complete()