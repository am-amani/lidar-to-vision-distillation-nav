import torch
import numpy as np
from torchvision.transforms import Compose, Resize, ToTensor, Normalize, RandomResizedCrop, ColorJitter, AutoAugment, AutoAugmentPolicy 
from PIL import Image
import cv2
from distillation_CNNs import CNN_FeatureExtractor_Camera, CNN_FeatureExtractor_Scan, Encoder, Actor_model
from replay_buffer import ReplayBuffer
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
import os
import traceback
from tensorboardX import SummaryWriter
import datetime

device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
print("Device:", device)



OUTPUT_DIM = 5
LR = 5e-5
BATCH_SIZE_TOTAL = 100
BATCH_SIZE_PER_BUFFER = BATCH_SIZE_TOTAL // 2
TRAIN_RATIO = 0.85
MAX_TRAIN_STEPS_PER_EPOCH = 300
SAVE_EVERY_EPOCHS = 10
LOG_EVERY_TRAIN_STEPS = 20
TRAIN_STEP = 0
EPOCH_STEP = 0
seed = 3407
torch.manual_seed(seed)
torch.cuda.manual_seed_all(seed)

print(f"Configured total batch size: {BATCH_SIZE_TOTAL}")
print(f"Per-buffer batch size (Pioneer/Waffel): {BATCH_SIZE_PER_BUFFER}/{BATCH_SIZE_PER_BUFFER}")
print(f"Max train steps per epoch: {MAX_TRAIN_STEPS_PER_EPOCH}")
print(f"Save checkpoint every epochs: {SAVE_EVERY_EPOCHS}")

date = datetime.datetime.now().strftime("%d.%h.%H.%M")

dirPath = os.path.dirname(os.path.realpath(__file__))
BUFFER_DIR = os.environ.get('REPLAY_BUFFER_DIR', os.path.join(dirPath, 'pytorch_models'))
PIONEER_BUFFER_FILE = 'Replay_Buffer_Pioneer_Part1_first250k.pth'
WAFFEL_BUFFER_FILE = 'replay_buffer_new_waffel_200_01_Part22_first250k.pth'

replay_buffer1 = torch.load(os.path.join(BUFFER_DIR, PIONEER_BUFFER_FILE))
print("replay_buffer1.size():", replay_buffer1.size())

replay_buffer4 = torch.load(os.path.join(BUFFER_DIR, WAFFEL_BUFFER_FILE))

print("replay_buffer4.size():", replay_buffer4.size())



replay_buffer_piooner = replay_buffer1
replay_buffer_waffel = replay_buffer4


def split_replay_buffer(replay_buffer, train_ratio=TRAIN_RATIO):
    all_data = list(replay_buffer.buffer)  # Convert deque to a list for easier handling
    
    np.random.shuffle(all_data)  # Ensure random order
    
    total_count = len(all_data)
    train_count = int(total_count * train_ratio)
    test_count = total_count - train_count  # This ensures the correct split
    
    train_data = all_data[:train_count]
    test_data = all_data[train_count:]  # Note: This should automatically give the rest of the data to the test set
    
    train_buffer = ReplayBuffer(replay_buffer.size())
    test_buffer = ReplayBuffer(replay_buffer.size())
    
    for experience in train_data:
        train_buffer.add(*experience)
    for experience in test_data:
        test_buffer.add(*experience)
    
    return train_buffer, test_buffer, train_count, test_count  # Return the actual counts for verification

train_buffer_piooner, test_buffer_piooner, train_count_piooner, test_count_piooner = split_replay_buffer(replay_buffer_piooner)
train_buffer_waffel, test_buffer_waffel, train_count_waffel, test_count_waffel = split_replay_buffer(replay_buffer_waffel)

experiment_name = (
    f"Nets{seed}_{date}_CamNoID_LidarWithID"
    f"_Pio{train_count_piooner}T{test_count_piooner}"
    f"_Waf{train_count_waffel}T{test_count_waffel}"
    f"_B{BATCH_SIZE_TOTAL}_R{int(TRAIN_RATIO * 100)}"
)
log_dir = os.path.join(dirPath, "runs", "new_runs", experiment_name)
save_path = log_dir
os.makedirs(save_path, exist_ok=True)
print("Experiment:", experiment_name)
print("TensorBoard logdir:", os.path.join("runs", "new_runs", experiment_name))


transform_camera = Compose([
    Resize((32, 64)),
    ToTensor(),
    Normalize(mean=[0.5], std=[0.5])
])

model_camera = CNN_FeatureExtractor_Camera().to(device)
model_camera_optimizer = optim.Adam(model_camera.parameters(), lr=LR, weight_decay=1e-5)

model_scan = CNN_FeatureExtractor_Scan().to(device)
model_scan_optimizer = optim.Adam(model_scan.parameters(), lr=LR, weight_decay=1e-5)

model_encoder = Encoder(OUTPUT_DIM).to(device)
model_encoder_optimizer = optim.Adam(model_encoder.parameters(), lr=LR, weight_decay=1e-5)


dim = 4 + OUTPUT_DIM + 32 + 1 # "+1": is because I have added robot ID

model_actor = Actor_model(dim, 2).to(device)
model_actor_optimizer = optim.Adam(model_actor.parameters(), lr=LR, weight_decay=1e-5)

writer = SummaryWriter(log_dir)
status_log_path = os.path.join(log_dir, "run_status.txt")

def scalar_value(value):
    if torch.is_tensor(value):
        return float(value.detach().cpu().item())
    return float(value)

def write_status(message):
    with open(status_log_path, "a", encoding="utf-8") as status_file:
        status_file.write(f"{datetime.datetime.now().isoformat(timespec='seconds')} {message}\n")

write_status("run_started")

def save_checkpoint(label):
    fename = os.path.join(save_path, label)
    model_camera.save_model(fename)
    model_scan.save_model(fename)
    model_encoder.save_model(fename)
    model_actor.save_model(fename)
    write_status(f"saved_checkpoint={label}")

    print(f"Saved checkpoint: {fename}", flush=True)

def combine_batches(batch1, batch2):
    return tuple(np.concatenate((b1, b2)) for b1, b2 in zip(batch1, batch2))


def sample_with_robot_id(replay_buffer, batch_size, robot_id):
    """Support both replay buffer APIs:
    - sample_batch(batch_size, robot_id) -> returns 8 items
    - sample_batch(batch_size) -> returns 7 items, so append robot_id here
    """
    try:
        return replay_buffer.sample_batch(batch_size, robot_id)
    except TypeError:
        batch = replay_buffer.sample_batch(batch_size)
        if len(batch) == 8:
            return batch
        robot_id_batch = np.full((len(batch[0]), 1), robot_id)
        return (*batch, robot_id_batch)

def train(data_batch):
    
    state_data_batch = torch.tensor(data_batch[0], dtype=torch.float32).to(device)
    state_data_batch = state_data_batch[:, 20:24]
    
    action_data_batch = torch.tensor(data_batch[1], dtype=torch.float32).to(device)
    
    robot_id_batch = torch.tensor(data_batch[7], dtype=torch.float32).to(device)
    


    global TRAIN_STEP
    

    if TRAIN_STEP % 2 == 0: #if it is even, then set the camera data to the model
        camera_data_batch = torch.stack([
            transform_camera(Image.fromarray(camera_data.squeeze().astype(np.uint8))) for camera_data in data_batch[5]]).to(device)        
    
        features = model_camera(camera_data_batch)
        encoded_features = model_encoder(features)
        camera_robot_token = torch.zeros_like(robot_id_batch)
        concatenated_all_camera = torch.cat((camera_robot_token, features, encoded_features, state_data_batch), 1).to(device)

        loss_mse_camera = F.mse_loss(model_actor(concatenated_all_camera), action_data_batch)
        if TRAIN_STEP % LOG_EVERY_TRAIN_STEPS == 0:
            print("MSE_LOSS_CAMERA/TRAIN:", loss_mse_camera, TRAIN_STEP, flush=True)
        
        model_camera_optimizer.zero_grad(set_to_none=True)
        model_encoder_optimizer.zero_grad(set_to_none=True)
        model_actor_optimizer.zero_grad(set_to_none=True)
        
        loss_mse_camera.backward()
        
        model_camera_optimizer.step()
        model_encoder_optimizer.step()
        model_actor_optimizer.step()
        

        

    else: #if it is odd, then set the scan data to the model
        num_sections = 20
        section_length = 360 // num_sections
        
        min_values_per_scan = [
            [min(scan_data[i * section_length:(i + 1) * section_length])
             for i in range(num_sections)]
            for scan_data in data_batch[6]
        ]
        
        scan_data_batch = torch.tensor(min_values_per_scan, dtype=torch.float32).view(-1, 1, num_sections).to(device)


        features = model_scan(scan_data_batch)
        encoded_features = model_encoder(features)
        concatenated_all_scan = torch.cat((robot_id_batch, features, encoded_features, state_data_batch), 1).to(device)
        
        loss_mse_scan = F.mse_loss(model_actor(concatenated_all_scan), action_data_batch)
        if TRAIN_STEP % LOG_EVERY_TRAIN_STEPS == 0:
            print("MSE_LOSS_SCAN/TRAIN:", loss_mse_scan, TRAIN_STEP, flush=True)
        




        
        model_scan_optimizer.zero_grad(set_to_none=True)
        model_encoder_optimizer.zero_grad(set_to_none=True)
        model_actor_optimizer.zero_grad(set_to_none=True)
        
        loss_mse_scan.backward()
        
        
        model_scan_optimizer.step()
        model_encoder_optimizer.step()
        model_actor_optimizer.step()
        


        

    
    TRAIN_STEP += 1
    if TRAIN_STEP % LOG_EVERY_TRAIN_STEPS == 0:
        write_status(f"train_step={TRAIN_STEP}")

def evaluate(data_batch):

    global EPOCH_STEP

    state_data_batch = torch.tensor(data_batch[0], dtype=torch.float32).to(device)
    state_data_batch = state_data_batch[:, 20:24]

    action_data_batch = torch.tensor(data_batch[1], dtype=torch.float32).to(device)
    robot_id_batch = torch.tensor(data_batch[7], dtype=torch.float32).to(device)

    if EPOCH_STEP >= 0: #if it is even, then set the camera data to the model
        with torch.no_grad():
            camera_data_batch = torch.stack([
                transform_camera(Image.fromarray(camera_data.squeeze().astype(np.uint8))) for camera_data in data_batch[5]]).to(device)        

            features_camera = model_camera(camera_data_batch)
            encoded_features_camera = model_encoder(features_camera)
            camera_robot_token = torch.zeros_like(robot_id_batch)
            concatenated_all_camera = torch.cat((camera_robot_token, features_camera, encoded_features_camera, state_data_batch), 1).to(device)

            predicted_camera_action = model_actor(concatenated_all_camera)
            loss_mse_camera = F.mse_loss(predicted_camera_action, action_data_batch)
            loss_l1_camera = F.l1_loss(predicted_camera_action, action_data_batch)
            print("///////////////////////////////////////////////////////////////////////////////////")
            print("MSE_LOSS_CAMERA/EPOCH:", loss_mse_camera, EPOCH_STEP)
            print("L1_LOSS_CAMERA/EPOCH:", loss_l1_camera, EPOCH_STEP) 
            print("///////////////////////////////////////////////////////////////////////////////////")
            
            num_sections = 20
            section_length = 360 // num_sections

            min_values_per_scan = [
                [min(scan_data[i * section_length:(i + 1) * section_length])
                 for i in range(num_sections)]
                for scan_data in data_batch[6]
            ]
            scan_data_batch = torch.tensor(min_values_per_scan, dtype=torch.float32).view(-1, 1, num_sections).to(device)
            
            features_scan = model_scan(scan_data_batch)
            encoded_features_scan = model_encoder(features_scan)
            concatenated_all_scan = torch.cat((robot_id_batch, features_scan, encoded_features_scan, state_data_batch), 1).to(device)


            predicted_scan_action = model_actor(concatenated_all_scan)
            loss_mse_scan = F.mse_loss(predicted_scan_action, action_data_batch)
            loss_l1_scan = F.l1_loss(predicted_scan_action, action_data_batch)
            validation_mse = (loss_mse_camera + loss_mse_scan) / 2.0
            writer.add_scalar('MODEL_SELECTION/VALIDATION_MSE', scalar_value(validation_mse), EPOCH_STEP)
            print("///////////////////////////////////////////////////////////////////////////////////")
            print("L1_LOSS_SCAN/EPOCH:", loss_l1_scan, EPOCH_STEP)
            print("MSE_LOSS_SCAN/EPOCH:", loss_mse_scan, EPOCH_STEP)
            print("MODEL_SELECTION/VALIDATION_MSE:", validation_mse, EPOCH_STEP)
            print("///////////////////////////////////////////////////////////////////////////////////")

  



    else: #if it is odd, then set the scan data to the model
        print("It is training with scan!!!!!!!")
        with torch.no_grad():
            num_sections = 20
            section_length = 360 // num_sections

            min_values_per_scan = [
                [min(scan_data[i * section_length:(i + 1) * section_length])
                 for i in range(num_sections)]
                for scan_data in data_batch[6]
            ]
            scan_data_batch = torch.tensor(min_values_per_scan, dtype=torch.float32).view(-1, 1, num_sections).to(device)
            
            features = model_scan(scan_data_batch)
            encoded_features = model_encoder(features)
            concatenated_all_scan = torch.cat((features, encoded_features, state_data_batch), 1).to(device)


            loss_mse_scan = F.mse_loss(model_actor(concatenated_all_scan), action_data_batch)
            loss_l1_scan = F.l1_loss(model_actor(concatenated_all_scan), action_data_batch)
            writer.add_scalar('MSE_LOSS_SCAN/EPOCH', loss_mse_scan, EPOCH_STEP)
            writer.add_scalar('L1_LOSS_SCAN/EPOCH', loss_l1_scan, EPOCH_STEP)
            print("///////////////////////////////////////////////////////////////////////////////////")
            print("L1_LOSS_SCAN/EPOCH:", loss_l1_scan, EPOCH_STEP)
            print("MSE_LOSS_SCAN/EPOCH:", loss_mse_scan, EPOCH_STEP)
            print("///////////////////////////////////////////////////////////////////////////////////")

            


    EPOCH_STEP += 1
    write_status(f"epoch_eval={EPOCH_STEP}")
    
    
ROBOT_ID_PIONEER = 1
ROBOT_ID_WAFFEL = 2
         
print("total train size: ", train_buffer_piooner.size() + train_buffer_waffel.size())
iter = min((train_buffer_piooner.size() + train_buffer_waffel.size()) // BATCH_SIZE_TOTAL, MAX_TRAIN_STEPS_PER_EPOCH)
print("iter:", iter)
epochs = int(os.environ.get("DISTILLATION_EPOCHS", 10000))
try:
    for epoch in range(epochs):
        print("Progress: %d%%, Epoch: %d" % ((epoch/epochs)*100, epoch), end="\r") 
        for i in range(iter):
            train_batch_pioneer = sample_with_robot_id(train_buffer_piooner, BATCH_SIZE_PER_BUFFER, ROBOT_ID_PIONEER)
            train_batch_waffel = sample_with_robot_id(train_buffer_waffel, BATCH_SIZE_PER_BUFFER, ROBOT_ID_WAFFEL)

            sample_batch_train = combine_batches(train_batch_pioneer, train_batch_waffel)        
            train(sample_batch_train)
        
        

        test_batch_pioneer = sample_with_robot_id(test_buffer_piooner, BATCH_SIZE_PER_BUFFER, ROBOT_ID_PIONEER)
        test_batch_waffel = sample_with_robot_id(test_buffer_waffel, BATCH_SIZE_PER_BUFFER, ROBOT_ID_WAFFEL)
        
        sample_batch_test = combine_batches(test_batch_pioneer, test_batch_waffel)
        evaluate(sample_batch_test)
        writer.flush()
        if EPOCH_STEP % SAVE_EVERY_EPOCHS == 0:
            ename = "epoch %d.dat" % (EPOCH_STEP)
            save_checkpoint(ename)
except Exception:
    write_status("python_exception")
    print("Training crashed with this error:", flush=True)
    traceback.print_exc()
    writer.flush()
    raise


        

print("Progress: 100%, Epoch: %d" % (epoch))
print("Training is done!")
ename = "epoch %d.dat" % (epoch)
save_checkpoint(ename)
    
    
