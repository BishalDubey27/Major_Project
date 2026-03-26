import argparse
import train_nn

parser = argparse.ArgumentParser(description="INCLUDE trainer for transformer")
parser.add_argument("--seed", default=0, type=int)
parser.add_argument("--dataset", default="include50", type=str, help="include or include50")
parser.add_argument("--use_augs", action="store_true")
parser.add_argument("--model", default="transformer", type=str)
parser.add_argument("--data_dir", required=True, type=str)
parser.add_argument("--save_path", default="./", type=str)
parser.add_argument("--epochs", default=50, type=int)
parser.add_argument("--batch_size", default=128, type=int)
parser.add_argument("--learning_rate", default=1e-4, type=float)
parser.add_argument("--transformer_size", default="small", type=str, help="small or large")
args = parser.parse_args()

if __name__ == "__main__":
    print("### Starting training ###")
    save_path = train_nn.fit(args)
    print("### Evaluating ###")
    train_nn.evaluate(args)
