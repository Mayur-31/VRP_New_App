function kamal {
    docker run -it --rm `
    -v "${PWD}:/workdir" `
    -e "DOCKER_HOST=tcp://host.docker.internal:2375" `
    -e "KAMAL_REGISTRY_PASSWORD=$env:KAMAL_REGISTRY_PASSWORD" `
    -e "OPENCAGE_API_KEY=$env:OPENCAGE_API_KEY" `
    --workdir /workdir `
    ghcr.io/basecamp/kamal:latest @args
}