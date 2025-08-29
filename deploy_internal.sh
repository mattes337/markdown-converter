#!/bin/sh
set -e

echo "=== Internal Container Deployment ==="

# Check if APIFY_TOKEN is set
if [ -z "$APIFY_TOKEN" ]; then
    echo "Error: APIFY_TOKEN environment variable is required"
    exit 1
fi

# Login to Apify
echo "Logging in to Apify..."
apify login --token "$APIFY_TOKEN"

# List of actors to deploy
#ACTORS="clean_html convert_by_body convert_by_url dereference_url"
ACTORS="search_to_markdown"

successful_count=0
failed_count=0
successful_actors=""
failed_actors=""

for actor in $ACTORS; do
    echo ""
    echo "=== Processing actor: $actor ==="
    
    actor_dir="/workspace/actors/$actor"
    
    if [ ! -d "$actor_dir" ]; then
        echo "Actor directory $actor_dir not found, skipping"
        failed_count=$((failed_count + 1))
        failed_actors="$failed_actors $actor"
        continue
    fi
    
    # Copy shared directory into actor directory
    echo "Copying shared code to $actor_dir/shared"
    cp -r /workspace/shared "$actor_dir/shared"
    
    # Modify main.py to use local shared directory
    main_py="$actor_dir/main.py"
    if [ -f "$main_py" ]; then
        echo "Modifying imports in $main_py"
        
        # Create backup
        cp "$main_py" "$main_py.backup"
        
        # Replace sys.path.append line to use local shared directory
        sed -i "s|sys\.path\.append(os\.path\.join(os\.path\.dirname(__file__), '\.\.', '\.\.', 'shared'))|sys.path.append(os.path.join(os.path.dirname(__file__), 'shared'))|g" "$main_py"
        
        echo "Modified imports in $main_py"
    fi
    
    # Copy root requirements.txt if actor doesn't have one
    if [ ! -f "$actor_dir/requirements.txt" ] && [ -f "/workspace/requirements.txt" ]; then
        echo "Copying root requirements.txt to $actor_dir"
        cp "/workspace/requirements.txt" "$actor_dir/requirements.txt"
    fi
    
    # Change to actor directory and push
    cd "$actor_dir"
    
    echo "Pushing $actor to Apify..."
    if apify push; then
        echo "Successfully pushed $actor to Apify"
        successful_count=$((successful_count + 1))
        successful_actors="$successful_actors $actor"
    else
        echo "Failed to push $actor to Apify"
        failed_count=$((failed_count + 1))
        failed_actors="$failed_actors $actor"
    fi
    
    # Return to workspace
    cd /workspace
done

echo ""
echo "=== Deployment Summary ==="

if [ $successful_count -gt 0 ]; then
    echo "Successfully deployed $successful_count actors:"
    for actor in $successful_actors; do
        echo "  ✓ $actor"
    done
fi

if [ $failed_count -gt 0 ]; then
    echo ""
    echo "Failed to deploy $failed_count actors:"
    for actor in $failed_actors; do
        echo "  ✗ $actor"
    done
    echo ""
    echo "Deployment completed with errors."
    exit 1
else
    echo ""
    echo "🎉 All actors deployed successfully!"
fi

echo ""
echo "Deployment completed!"