FROM docker.io/library/python
RUN ["useradd", "--create-home", "user"]
USER user:user
RUN ["mkdir", "/home/user/veil-edit"]
WORKDIR /home/user/veil-edit
COPY --chown=user:user [".", "."]
RUN ["./docker.sh"]
