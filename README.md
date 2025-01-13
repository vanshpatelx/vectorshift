# VectorShift HubSpot Integration

## Video Presentation
**Link:** [Watch here](https://youtu.be/sOVvrjLJP-8)

## Development Time: 3 Hours

## Worked (Tech Stack)
- **Code:** NodeJS, GoLang, Python (for writing scraper engines), ReactJS (Beginner level)
- **DevOps Tools:** Docker, Kubernetes (K8s), Terraform, Helm, AWS, CI/CD

## Experience Summary
I have extensive experience working in multiple startups, contributing across the entire product lifecycle—from idea conception to system design, code implementation, and DevOps.

## Implemented Features
### 1. HubSpot Authorization Initiation
- Generates a unique state and encodes it.
- Stores the state in Redis.
- Returns an authorization URL for user authentication.

### 2. OAuth2 Callback Handling
- Handles the OAuth2 callback from HubSpot.
- Validates the state received from HubSpot.
- Exchanges the authorization code for an access token.

### 3. HubSpot Credential Retrieval
- Retrieves access credentials from Redis for a specific user and organization.
- Validates the credentials' format before returning them.

### 4. IntegrationItem Metadata Creation
- Creates an IntegrationItem object from HubSpot API response data.
- Includes optional fields like parent ID and name.

### 5. Recursive Item Fetching from HubSpot API
- Retrieves paginated items from the HubSpot API.
- Appends the items to a list for further processing.

### 6. HubSpot Companies Retrieval
- Uses stored credentials to retrieve a list of company data from HubSpot.
- Converts the company data into IntegrationItem objects for further use.

