# Snowflake Authentication

## Méthodes d'authentification

Le `SnowflakeConnector` supporte deux méthodes d'authentification, en privilégiant l'authentification par clé privée.

### 1. Authentification par clé privée (Recommandé) 🔑

Cette méthode est plus sécurisée et recommandée pour les environnements de production.

#### Génération de la paire de clés

```bash
# 1. Générer la clé privée (avec passphrase)
openssl genrsa -out snowflake_key.pem 2048

# Ou avec chiffrement (recommandé)
openssl genrsa -aes256 -out snowflake_key.pem 2048

# 2. Générer la clé publique
openssl rsa -in snowflake_key.pem -pubout -out snowflake_key.pub

# 3. Afficher la clé publique (à copier dans Snowflake)
cat snowflake_key.pub | grep -v "BEGIN PUBLIC" | grep -v "END PUBLIC" | tr -d '\n'
```

#### Configuration dans Snowflake

```sql
-- Associer la clé publique à votre utilisateur
ALTER USER <username> SET RSA_PUBLIC_KEY='<votre_clé_publique>';

-- Vérifier
DESC USER <username>;
```

#### Variables d'environnement

```bash
export SNOWFLAKE_ACCOUNT=<your_account>
export SNOWFLAKE_USER=<your_user>
export SNOWFLAKE_ROLE=<your_role>
export SNOWFLAKE_PRIVATE_KEY_PATH=/path/to/snowflake_key.pem
export SNOWFLAKE_PRIVATE_KEY_PASSPHRASE=<your_passphrase>  # Optionnel si la clé n'est pas chiffrée
export SNOWFLAKE_WAREHOUSE=<your_warehouse>  # Optionnel
export SNOWFLAKE_DATABASE=<your_database>    # Optionnel
```

#### Exemple de fichier .env

```bash
# .env
SNOWFLAKE_ACCOUNT=xy12345.us-east-1
SNOWFLAKE_USER=john_doe
SNOWFLAKE_ROLE=SYSADMIN
SNOWFLAKE_PRIVATE_KEY_PATH=./keys/snowflake_key.pem
SNOWFLAKE_PRIVATE_KEY_PASSPHRASE=my_secure_passphrase
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
SNOWFLAKE_DATABASE=NUTRIRAG_PROJECT
```

### 2. Authentification par mot de passe (Fallback) 🔐

Si aucune clé privée n'est fournie, le système utilisera l'authentification par mot de passe.

#### Variables d'environnement

```bash
export SNOWFLAKE_ACCOUNT=<your_account>
export SNOWFLAKE_USER=<your_user>
export SNOWFLAKE_PASSWORD=<your_password>
export SNOWFLAKE_ROLE=<your_role>
export SNOWFLAKE_WAREHOUSE=<your_warehouse>  # Optionnel
export SNOWFLAKE_DATABASE=<your_database>    # Optionnel
```

## Utilisation

```python
from SnowflakeConnector import SnowflakeConnector

# Le connector détecte automatiquement la méthode d'authentification
connector = SnowflakeConnector()

# Utiliser la connexion
df = connector.session.table("MY_DATABASE.MY_SCHEMA.MY_TABLE").to_pandas()

# Fermer la session
connector.close()
```

## Sécurité

### Bonnes pratiques

1. **Ne jamais commiter les clés privées** dans le dépôt Git
2. **Ajouter les clés au .gitignore**:
   ```
   *.pem
   *.key
   .env
   ```
3. **Utiliser des passphrases fortes** pour chiffrer les clés privées
4. **Stocker les clés dans un gestionnaire de secrets** en production (AWS Secrets Manager, Azure Key Vault, etc.)
5. **Restreindre les permissions** sur les fichiers de clés:
   ```bash
   chmod 600 snowflake_key.pem
   ```

### Rotation des clés

Il est recommandé de changer régulièrement les clés:

```sql
-- Supprimer l'ancienne clé
ALTER USER <username> UNSET RSA_PUBLIC_KEY;

-- Ajouter la nouvelle clé
ALTER USER <username> SET RSA_PUBLIC_KEY='<nouvelle_clé_publique>';
```

## Dépendances

Pour l'authentification par clé privée, assurez-vous d'avoir installé:

```bash
pip install cryptography
```

## Dépannage

### Erreur "Private key object is not supported"

- Vérifiez que la clé est au format PEM
- Vérifiez que le passphrase est correct

### Erreur "JWT token is invalid"

- La clé publique dans Snowflake ne correspond pas à la clé privée utilisée
- Reconfigurer la clé publique dans Snowflake

### Erreur de connexion

```bash
# Tester la connexion avec snowsql
snowsql -a <account> -u <user> --private-key-path snowflake_key.pem
```
