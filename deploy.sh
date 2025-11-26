#!/bin/bash

# ToS Monitor - Cloud Run Deployment Script
# Simple wrapper for deploy_to_cloudrun.py

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Function to print colored output
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Function to show help
show_help() {
    echo "ToS Monitor - Cloud Run Deployment"
    echo ""
    echo "Usage: ./deploy.sh [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --dry-run       Show what would be deployed without actually deploying"
    echo "  --skip-build    Skip building image and deploy existing image"
    echo "  --local-build   Use local Docker instead of Google Cloud Build"
    echo "  --help, -h      Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./deploy.sh                 # Full deployment"
    echo "  ./deploy.sh --dry-run       # Test what would be deployed"
    echo "  ./deploy.sh --skip-build    # Deploy without rebuilding"
    echo "  ./deploy.sh --local-build   # Use local Docker build"
    echo ""
}

# Check if Python deployment script exists
check_prerequisites() {
    if [[ ! -f "$SCRIPT_DIR/deploy_to_cloudrun.py" ]]; then
        print_error "deploy_to_cloudrun.py not found in $SCRIPT_DIR"
        exit 1
    fi

    if [[ ! -f "$SCRIPT_DIR/.env" ]]; then
        print_warning ".env file not found. Make sure your environment variables are set."
        print_info "You can copy deploy-config.env.example to .env and customize it."
    fi

    # Check if Python is available
    if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
        print_error "Python is not installed or not in PATH"
        exit 1
    fi

    # Use python3 if available, otherwise python
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    else
        PYTHON_CMD="python"
    fi
}

# Main deployment function
deploy() {
    local args=("$@")

    print_info "Starting ToS Monitor deployment..."
    print_info "Working directory: $SCRIPT_DIR"

    # Change to script directory
    cd "$SCRIPT_DIR"

    # Run the Python deployment script
    if [[ ${#args[@]} -eq 0 ]]; then
        print_info "Running full deployment (build + deploy)"
        $PYTHON_CMD deploy_to_cloudrun.py
    else
        print_info "Running deployment with options: ${args[*]}"
        $PYTHON_CMD deploy_to_cloudrun.py "${args[@]}"
    fi

    if [[ $? -eq 0 ]]; then
        print_success "Deployment completed successfully!"
    else
        print_error "Deployment failed!"
        exit 1
    fi
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --help|-h)
                show_help
                exit 0
                ;;
            --dry-run)
                ARGS+=("--dry-run")
                shift
                ;;
            --skip-build)
                ARGS+=("--skip-build")
                shift
                ;;
            --local-build)
                ARGS+=("--local-build")
                shift
                ;;
            *)
                print_error "Unknown option: $1"
                echo ""
                show_help
                exit 1
                ;;
        esac
    done
}

# Main execution
main() {
    # Array to store arguments
    ARGS=()

    # Parse command line arguments
    parse_args "$@"

    # Check prerequisites
    check_prerequisites

    # Run deployment
    deploy "${ARGS[@]}"
}

# Handle Ctrl+C gracefully
trap 'print_warning "Deployment interrupted by user"; exit 130' INT

# Run main function with all arguments
main "$@"