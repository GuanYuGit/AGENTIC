terraform {
  required_version = ">= 1.6.0"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}

provider "aws" {
  region = var.region
}

# Inputs
variable "project_name" { type = string }
variable "region"       { type = string }
variable "vpc_id"       { type = string }
variable "public_subnet_ids" { type = list(string) }
variable "desired_count" { type = number, default = 1 }

# ECR Repos
resource "aws_ecr_repository" "api" {
  name = "${var.project_name}-api"
  image_scanning_configuration { scan_on_push = true }
}

# ECS Cluster
resource "aws_ecs_cluster" "this" {
  name = var.project_name
}

# IAM Roles
resource "aws_iam_role" "task_execution" {
  name = "${var.project_name}-task-exec"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{ Action = "sts:AssumeRole", Effect = "Allow", Principal = { Service = "ecs-tasks.amazonaws.com" } }]
  })
}
resource "aws_iam_role_policy_attachment" "exec_policy" {
  role       = aws_iam_role.task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role" "task_role" {
  name = "${var.project_name}-task-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{ Action = "sts:AssumeRole", Effect = "Allow", Principal = { Service = "ecs-tasks.amazonaws.com" } }]
  })
}

# Allow Bedrock access
resource "aws_iam_role_policy" "bedrock_access" {
  name = "${var.project_name}-bedrock-access"
  role = aws_iam_role.task_role.id
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect = "Allow",
      Action = ["bedrock:InvokeModel", "bedrock:Converse"],
      Resource = "*"
    }]
  })
}

# Security Groups
resource "aws_security_group" "alb_sg" {
  name   = "${var.project_name}-alb-sg"
  vpc_id = var.vpc_id
  ingress { from_port = 80 to_port = 80 protocol = "tcp" cidr_blocks = ["0.0.0.0/0"] }
  egress  { from_port = 0  to_port = 0  protocol = "-1" cidr_blocks = ["0.0.0.0/0"] }
}
resource "aws_security_group" "ecs_sg" {
  name   = "${var.project_name}-ecs-sg"
  vpc_id = var.vpc_id
  ingress { from_port = 0 to_port = 65535 protocol = "tcp" security_groups = [aws_security_group.alb_sg.id] }
  egress  { from_port = 0 to_port = 0 protocol = "-1" cidr_blocks = ["0.0.0.0/0"] }
}

# ALB + listeners + target groups
resource "aws_lb" "this" {
  name               = "${var.project_name}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb_sg.id]
  subnets            = var.public_subnet_ids
}
resource "aws_lb_target_group" "api_tg" {
  name     = "${var.project_name}-api-tg"
  port     = 8080
  protocol = "HTTP"
  vpc_id   = var.vpc_id
  target_type = "ip"
  health_check { path = "/health" port = "8080" matcher = "200-399" }
}
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.this.arn
  port = 80
  protocol = "HTTP"
  default_action {
    type = "forward"
    target_group_arn = aws_lb_target_group.api_tg.arn
  }
}

# Task Definition
resource "aws_ecs_task_definition" "api" {
  family                   = "${var.project_name}-api"
  cpu                      = "2048"
  memory                   = "4096"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  execution_role_arn       = aws_iam_role.task_execution.arn
  task_role_arn            = aws_iam_role.task_role.arn
  container_definitions = jsonencode([{
    name      = "api"
    image     = "${aws_ecr_repository.api.repository_url}:latest"
    essential = true
    portMappings = [{ containerPort = 8080, hostPort = 8080 }]
    environment = [
      { name = "AWS_REGION", value = var.region },
      { name = "PROJECT_ROOT", value = "/app" }
    ]
    logConfiguration = {
      logDriver = "awslogs",
      options = {
        awslogs-group         = "/ecs/${var.project_name}-api",
        awslogs-region        = var.region,
        awslogs-stream-prefix = "ecs"
      }
    }
  }])
}

# Log groups
resource "aws_cloudwatch_log_group" "api" { 
  name = "/ecs/${var.project_name}-api" 
  retention_in_days = 14 
}

# ECS Service
resource "aws_ecs_service" "api" {
  name            = "${var.project_name}-api"
  cluster         = aws_ecs_cluster.this.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"
  network_configuration {
    subnets         = var.public_subnet_ids
    security_groups = [aws_security_group.ecs_sg.id]
    assign_public_ip = true
  }
  load_balancer {
    target_group_arn = aws_lb_target_group.api_tg.arn
    container_name   = "api"
    container_port   = 8080
  }
  depends_on = [aws_lb_listener.http]
}

output "alb_dns_name" {
  value = aws_lb.this.dns_name
}
output "api_url" {
  value = "http://${aws_lb.this.dns_name}"
}
