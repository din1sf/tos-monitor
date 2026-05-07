#!/bin/bash
set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Default values
DEFAULT_ENV_FILE=".env.cloud"
SKIP_MENU=false
DRY_RUN=false
SKIP_BUILD=false
USE_LOCAL_BUILD=false
ENV_FILE=""

# Print functions
print_header() {
    echo -e "\n${CYAN}╔════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║  ToS Monitor - Cloud Run Deployment   ║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════╝${NC}\n"
}

print_info() { echo -e "${BLUE}ℹ${NC}  $1"; }
print_success() { echo -e "${GREEN}✓${NC}  $1"; }
print_warning() { echo -e "${YELLOW}⚠${NC}  $1"; }
print_error() { echo -e "${RED}✗${NC}  $1"; }

# Parse command-line arguments (for non-interactive mode)
while [[ $# -gt 0 ]]; do
    case $1 in
        --env) ENV_FILE="$2"; SKIP_MENU=true; shift 2 ;;
        --skip-menu) SKIP_MENU=true; shift ;;
        --dry-run) DRY_RUN=true; shift ;;
        --skip-build) SKIP_BUILD=true; shift ;;
        --local-build) USE_LOCAL_BUILD=true; shift ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --env FILE       Use specific env file (implies --skip-menu)"
            echo "  --skip-menu      Skip interactive menu"
            echo "  --dry-run        Preview without deploying"
            echo "  --skip-build     Deploy without rebuilding image"
            echo "  --local-build    Use local Docker instead of Cloud Build"
            exit 0
            ;;
        *) print_error "Unknown option: $1"; exit 1 ;;
    esac
done

# Check prerequisites
check_prerequisites() {
    if ! command -v gcloud &> /dev/null; then
        print_error "gcloud CLI not found. Install from https://cloud.google.com/sdk"
        exit 1
    fi

    if [[ "$USE_LOCAL_BUILD" == true ]] && ! command -v docker &> /dev/null; then
        print_error "Docker not found but --local-build specified"
        exit 1
    fi

    print_success "Prerequisites check passed"
}

# Interactive menu for env file selection
select_env_file() {
    echo -e "\n${CYAN}Select environment file:${NC}"

    local files=()
    [[ -f ".env.cloud" ]] && files+=(".env.cloud (recommended)")
    [[ -f ".env" ]] && files+=(".env")
    files+=("Custom path...")

    local i=1
    for file in "${files[@]}"; do
        if [[ $i -eq 1 ]]; then
            echo -e "  ${GREEN}[$i]${NC} $file"
        else
            echo -e "  [$i] $file"
        fi
        ((i++))
    done

    echo -en "\n${CYAN}Choice [1]:${NC} "
    read -r choice
    choice=${choice:-1}

    case $choice in
        1) ENV_FILE=".env.cloud" ;;
        2) ENV_FILE=".env" ;;
        3)
            echo -en "${CYAN}Enter path:${NC} "
            read -r ENV_FILE
            ;;
        *) print_error "Invalid choice"; exit 1 ;;
    esac
}

# Interactive menu for deployment mode
select_deployment_mode() {
    echo -e "\n${CYAN}Deployment mode:${NC}"
    echo -e "  ${GREEN}[1]${NC} Full deployment (build + deploy)"
    echo -e "  [2] Deploy only (skip build)"
    echo -e "  [3] Dry run (preview only)"

    echo -en "\n${CYAN}Choice [1]:${NC} "
    read -r choice
    choice=${choice:-1}

    case $choice in
        1) SKIP_BUILD=false; DRY_RUN=false ;;
        2) SKIP_BUILD=true; DRY_RUN=false ;;
        3) DRY_RUN=true ;;
        *) print_error "Invalid choice"; exit 1 ;;
    esac
}

# Interactive menu for build method
select_build_method() {
    [[ "$SKIP_BUILD" == true ]] && return

    echo -e "\n${CYAN}Build method:${NC}"
    echo -e "  ${GREEN}[1]${NC} Cloud Build (recommended)"
    echo -e "  [2] Local Docker"

    echo -en "\n${CYAN}Choice [1]:${NC} "
    read -r choice
    choice=${choice:-1}

    case $choice in
        1) USE_LOCAL_BUILD=false ;;
        2) USE_LOCAL_BUILD=true ;;
        *) print_error "Invalid choice"; exit 1 ;;
    esac
}

# Load and validate env file
load_env_file() {
    if [[ ! -f "$ENV_FILE" ]]; then
        print_error "Environment file not found: $ENV_FILE"
        exit 1
    fi

    print_info "Loading environment from $ENV_FILE"
    set -a
    source "$ENV_FILE"
    set +a

    # Validate required variables
    local missing=()
    [[ -z "$GOOGLE_CLOUD_PROJECT" ]] && missing+=("GOOGLE_CLOUD_PROJECT")
    [[ -z "$STORAGE_BUCKET" ]] && missing+=("STORAGE_BUCKET")
    [[ -z "$SERVICE_NAME" ]] && missing+=("SERVICE_NAME")

    if [[ ${#missing[@]} -gt 0 ]]; then
        print_error "Missing required variables in $ENV_FILE: ${missing[*]}"
        exit 1
    fi

    # Set defaults
    CLOUD_RUN_REGION=${CLOUD_RUN_REGION:-europe-west3}
    SERVICE_NAME=${SERVICE_NAME:-tos-monitor}

    print_success "Environment loaded"
}

# Show deployment summary
show_summary() {
    echo -e "\n${CYAN}Deployment Summary:${NC}"
    echo -e "  • Env file:     ${GREEN}$ENV_FILE${NC}"
    echo -e "  • Project:      $GOOGLE_CLOUD_PROJECT"
    echo -e "  • Service:      $SERVICE_NAME"
    echo -e "  • Region:       $CLOUD_RUN_REGION"
    echo -e "  • Mode:         $([ "$DRY_RUN" = true ] && echo "Dry run" || echo "Deploy")"
    [[ "$SKIP_BUILD" == false ]] && echo -e "  • Build:        $([ "$USE_LOCAL_BUILD" = true ] && echo "Local Docker" || echo "Cloud Build")"

    if [[ "$DRY_RUN" == false && "$SKIP_MENU" == false ]]; then
        echo -en "\n${CYAN}Continue? [Y/n]:${NC} "
        read -r confirm
        if [[ "$confirm" =~ ^[Nn] ]]; then
            print_warning "Cancelled"
            exit 0
        fi
    fi
}

# Build image
build_image() {
    [[ "$SKIP_BUILD" == true ]] && return

    local image="gcr.io/$GOOGLE_CLOUD_PROJECT/$SERVICE_NAME"

    if [[ "$DRY_RUN" == true ]]; then
        print_info "Would build image: $image"
        return
    fi

    print_info "Building image: $image"

    if [[ "$USE_LOCAL_BUILD" == true ]]; then
        docker build -t "$image" . || { print_error "Docker build failed"; exit 1; }
        docker push "$image" || { print_error "Docker push failed"; exit 1; }
    else
        gcloud builds submit --tag "$image" --project "$GOOGLE_CLOUD_PROJECT" || {
            print_error "Cloud Build failed"
            exit 1
        }
    fi

    print_success "Image built and pushed"
}

# Deploy to Cloud Run
deploy_service() {
    local image="gcr.io/$GOOGLE_CLOUD_PROJECT/$SERVICE_NAME"

    local cmd=(gcloud run deploy "$SERVICE_NAME"
        --image "$image"
        --platform managed
        --region "$CLOUD_RUN_REGION"
        --project "$GOOGLE_CLOUD_PROJECT"
        --allow-unauthenticated
        --no-async
        --set-env-vars "STORAGE_MODE=cloud,STORAGE_BUCKET=$STORAGE_BUCKET,GOOGLE_CLOUD_PROJECT=$GOOGLE_CLOUD_PROJECT")

    # Add AI provider config
    if [[ -n "$AI_PROVIDER" ]]; then
        cmd+=(--set-env-vars "AI_PROVIDER=$AI_PROVIDER")
    fi

    # Bosch LLM Farm
    if [[ -n "$ANTHROPIC_AUTH_TOKEN" ]]; then
        cmd+=(--set-env-vars "ANTHROPIC_AUTH_TOKEN=$ANTHROPIC_AUTH_TOKEN")
    fi
    if [[ -n "$BOSCH_LLM_MODEL" ]]; then
        cmd+=(--set-env-vars "BOSCH_LLM_MODEL=$BOSCH_LLM_MODEL")
    fi
    if [[ -n "$BOSCH_LLM_BASE_URL" ]]; then
        cmd+=(--set-env-vars "BOSCH_LLM_BASE_URL=$BOSCH_LLM_BASE_URL")
    fi

    # OpenRouter
    if [[ -n "$OPENROUTER_API_KEY" ]]; then
        cmd+=(--set-env-vars "OPENROUTER_API_KEY=$OPENROUTER_API_KEY")
    fi
    if [[ -n "$OPENROUTER_MODEL" ]]; then
        cmd+=(--set-env-vars "OPENROUTER_MODEL=$OPENROUTER_MODEL")
    fi

    # OpenAI
    if [[ -n "$OPENAI_API_KEY" ]]; then
        cmd+=(--set-env-vars "OPENAI_API_KEY=$OPENAI_API_KEY")
    fi
    if [[ -n "$LLM_MODEL" ]]; then
        cmd+=(--set-env-vars "LLM_MODEL=$LLM_MODEL")
    fi

    # Application metadata
    if [[ -n "$APP_VERSION" ]]; then
        cmd+=(--set-env-vars "APP_VERSION=$APP_VERSION")
    fi

    if [[ "$DRY_RUN" == true ]]; then
        print_info "Would execute:"
        echo -e "${YELLOW}${cmd[*]}${NC}"
        return
    fi

    print_info "Deploying to Cloud Run..."
    "${cmd[@]}" || { print_error "Deployment failed"; exit 1; }

    # Get service URL
    local url=$(gcloud run services describe "$SERVICE_NAME" \
        --region "$CLOUD_RUN_REGION" \
        --project "$GOOGLE_CLOUD_PROJECT" \
        --format="value(status.url)" 2>/dev/null)

    if [[ -z "$url" ]]; then
        print_warning "Could not retrieve service URL"
        print_success "Deployment complete!"
        return
    fi

    # Verify service is responding
    print_info "Verifying service health..."
    local retries=0
    local max_retries=30
    while [[ $retries -lt $max_retries ]]; do
        if curl -sf "$url/health" > /dev/null 2>&1; then
            print_success "Service is healthy and responding!"
            break
        fi
        ((retries++))
        if [[ $retries -lt $max_retries ]]; then
            sleep 2
        else
            print_warning "Service deployed but health check timed out (may still be starting)"
        fi
    done

    print_success "Deployment complete!"
    echo -e "\n${GREEN}Service URL:${NC} $url"
    echo -e "${BLUE}Web UI:${NC}      $url/ui"
    echo -e "${BLUE}API Docs:${NC}    $url/docs"
}

# Main execution
main() {
    print_header
    check_prerequisites

    # Interactive menu (unless --skip-menu)
    if [[ "$SKIP_MENU" == false ]]; then
        [[ -z "$ENV_FILE" ]] && select_env_file
        select_deployment_mode
        select_build_method
    else
        # Non-interactive: use defaults if not specified
        [[ -z "$ENV_FILE" ]] && ENV_FILE="$DEFAULT_ENV_FILE"
    fi

    load_env_file
    show_summary
    build_image
    deploy_service

    echo -e "\n${GREEN}Done!${NC}\n"
}

main
