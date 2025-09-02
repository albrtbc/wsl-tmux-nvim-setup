#!/bin/bash
set -euo pipefail

# Script name for usage
SCRIPT_NAME=$(basename "$0")

# Default values (can be overridden)
# No default profile - must be specified
DEFAULT_REGION="eu-west-1"
DEFAULT_FRAMEWORK="net8.0"
DEFAULT_CONFIG="Release"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to display usage
usage() {
    cat << EOF
Usage: $SCRIPT_NAME [OPTIONS]

Deploy a .NET Lambda function to AWS

OPTIONS:
    -l, --lambda-name NAME       Lambda function name (required)
    -p, --project-path PATH      Project path relative to current directory (required)
    -P, --profile PROFILE        AWS SSO profile (required)
    -n, --project-name NAME      Project name (optional, defaults to last part of path)
    -r, --region REGION          AWS region (default: $DEFAULT_REGION)
    -f, --framework FRAMEWORK    .NET framework version (default: $DEFAULT_FRAMEWORK)
    -c, --config CONFIG          Build configuration (default: $DEFAULT_CONFIG)
    -h, --help                   Display this help message

EXAMPLES:
    # Basic usage (project name auto-derived from path)
    $SCRIPT_NAME -l MyLambda -p src/MyProject.API -P dev-profile

    # With explicit project name
    $SCRIPT_NAME -l MyLambda -p src/MyProject -n MyProject.API -P prod-profile

    # Using environment variables
    export LAMBDA_NAME="MyLambda"
    export PROJECT_PATH="src/MyProject.API"
    export PROFILE="dev-profile"
    $SCRIPT_NAME

ALIAS EXAMPLES:
    # Add to ~/.bashrc or ~/.zshrc
    alias deploy-log-retriever='$SCRIPT_NAME -l LogRetrieverApi -p src/Ohpen.Reporting.MonitoringNotifier.API -P dev-sentinel'
    alias deploy-my-api='$SCRIPT_NAME -l MyApi -p src/MyApi.Project -P prod-profile'

EOF
    exit 0
}

# Function to print colored messages
print_error() {
    echo -e "${RED}❌ $1${NC}" >&2
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}$1${NC}"
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -l|--lambda-name)
                LAMBDA_NAME="$2"
                shift 2
                ;;
            -p|--project-path)
                PROJECT_PATH="$2"
                shift 2
                ;;
            -n|--project-name)
                PROJECT_NAME="$2"
                shift 2
                ;;
            -P|--profile)
                PROFILE="$2"
                shift 2
                ;;
            -r|--region)
                REGION="$2"
                shift 2
                ;;
            -f|--framework)
                FRAMEWORK="$2"
                shift 2
                ;;
            -c|--config)
                CONFIG="$2"
                shift 2
                ;;
            -h|--help)
                usage
                ;;
            *)
                print_error "Unknown option: $1"
                echo "Use -h or --help for usage information"
                exit 1
                ;;
        esac
    done
}

# Validate required parameters
validate_params() {
    local missing_params=()
    
    # Check for required parameters (can also come from environment variables)
    if [[ -z "${LAMBDA_NAME:-}" ]]; then
        missing_params+=("LAMBDA_NAME (-l)")
    fi
    
    if [[ -z "${PROJECT_PATH:-}" ]]; then
        missing_params+=("PROJECT_PATH (-p)")
    fi
    
    if [[ -z "${PROFILE:-}" ]]; then
        missing_params+=("PROFILE (-P)")
    fi
    
    # Auto-derive project name from path if not specified
    if [[ -z "${PROJECT_NAME:-}" ]]; then
        PROJECT_NAME=$(basename "$PROJECT_PATH")
        print_info "📝 Using project name: $PROJECT_NAME"
    fi
    
    if [[ ${#missing_params[@]} -gt 0 ]]; then
        print_error "Missing required parameters:"
        for param in "${missing_params[@]}"; do
            echo "  - $param"
        done
        echo ""
        echo "Use -h or --help for usage information"
        exit 1
    fi
    
    # Validate project path exists
    if [[ ! -d "$PROJECT_PATH" ]]; then
        print_error "Project path does not exist: $PROJECT_PATH"
        exit 1
    fi
    
    # Validate project file exists
    if [[ ! -f "$PROJECT_PATH/$PROJECT_NAME.csproj" ]]; then
        print_error "Project file not found: $PROJECT_PATH/$PROJECT_NAME.csproj"
        exit 1
    fi
}

# Function to ensure AWS SSO session
ensure_sso() {
    # If current credentials don't work (or are expired), this will fail fast.
    if ! aws sts get-caller-identity --profile "$PROFILE" >/dev/null 2>&1; then
        print_info "🔐 SSO expired/missing. Logging in..."
        aws sso login --profile "$PROFILE"
    else
        # Optional: refresh if the exported creds expire in <5 minutes
        if EXP=$(aws configure export-credentials --profile "$PROFILE" --format json 2>/dev/null | jq -r '.Credentials.Expiration' 2>/dev/null); then
            now_s=$(date +%s)
            exp_s=$(date -d "$EXP" +%s 2>/dev/null || echo $((now_s+999999)))
            if (( exp_s - now_s < 300 )); then
                print_info "🔁 SSO token about to expire. Refreshing..."
                aws sso login --profile "$PROFILE"
            fi
        fi
    fi
}

# Main deployment function
deploy_lambda() {
    print_info "🚀 Starting deployment for $LAMBDA_NAME"
    echo "   Profile: $PROFILE"
    echo "   Region: $REGION"
    echo "   Project: $PROJECT_NAME"
    echo "   Path: $PROJECT_PATH"
    echo ""
    
    # Ensure AWS SSO session
    print_info "🔎 Ensuring AWS SSO session..."
    ensure_sso
    
    # Get AWS account ID
    print_info "🔎 Getting AWS account ID..."
    ACCOUNT_ID=$(aws sts get-caller-identity --profile "$PROFILE" --query "Account" --output text)
    echo "   Account ID: $ACCOUNT_ID"
    echo ""
    
    # Check if Lambda tools are installed
    if ! dotnet tool list -g | grep -q Amazon.Lambda.Tools; then
        print_info "📦 Installing Amazon Lambda Tools..."
        dotnet tool install -g Amazon.Lambda.Tools
    else
        print_success "Amazon Lambda Tools already installed"
    fi
    
    # Restore NuGet packages
    print_info "📦 Restoring NuGet packages..."
    dotnet restore "$PROJECT_PATH/$PROJECT_NAME.csproj"
    
    # Build and package Lambda
    print_info "🛠️ Building and publishing Lambda package..."
    cd "$PROJECT_PATH"
    
    # Create output directory if it doesn't exist
    mkdir -p "./bin/$CONFIG/$FRAMEWORK"
    
    # Use dotnet lambda package to create the deployment package
    dotnet lambda package \
        --configuration "$CONFIG" \
        --framework "$FRAMEWORK" \
        --output-package "./bin/$CONFIG/$FRAMEWORK/$PROJECT_NAME.zip"
    
    print_success "Lambda package created successfully"
    
    # Deploy to Lambda
    print_info "📤 Updating Lambda function $LAMBDA_NAME..."
    aws lambda update-function-code \
        --function-name "$LAMBDA_NAME" \
        --zip-file "fileb://./bin/$CONFIG/$FRAMEWORK/$PROJECT_NAME.zip" \
        --region "$REGION" \
        --profile "$PROFILE"
    
    print_success "Lambda function updated successfully"
    
    # Wait for update to complete
    print_info "⏳ Waiting for Lambda function update to complete..."
    aws lambda wait function-updated \
        --function-name "$LAMBDA_NAME" \
        --region "$REGION" \
        --profile "$PROFILE"
    
    print_success "🎉 Deployment completed successfully!"
}

# Main script execution
main() {
    # Set defaults (no default for PROFILE - must be provided)
    REGION="${REGION:-$DEFAULT_REGION}"
    FRAMEWORK="${FRAMEWORK:-$DEFAULT_FRAMEWORK}"
    CONFIG="${CONFIG:-$DEFAULT_CONFIG}"
    
    # Parse arguments (will override environment variables if provided)
    parse_args "$@"
    
    # Validate parameters
    validate_params
    
    # Execute deployment
    deploy_lambda
}

# Run main function
main "$@"
